from __future__ import annotations

from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from openai import AsyncOpenAI

from .const import DOMAIN, CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([OpenAIConversationEntity(entry)])


class OpenAIConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    _attr_supports_streaming = False

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        opts = self.entry.options
        client: AsyncOpenAI = self.entry.runtime_data  # type: ignore[attr-defined]

        # Provide LLM context and tools from HA to the model
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                opts.get("llm_hass_api"),
                opts.get("prompt"),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        # Convert HA LLM API tools to Responses API tools
        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = []
            for t in chat_log.llm_api.tools:
                tools.append(
                    {
                        "type": "function",
                        "name": t.name,
                        "description": getattr(t, "description", ""),
                        "parameters": getattr(t, "parameters", {}),
                    }
                )

        # Build Responses API input from chat log
        msgs: list[dict[str, Any]] = []
        for c in chat_log.content:
            role = "user" if getattr(c, "is_user", False) else "assistant"
            text = getattr(c, "content", "") or ""
            msgs.append(
                {
                    "type": "message",
                    "role": role,
                    "content": [
                        {
                            "type": "input_text",
                            "text": text,
                        }
                    ],
                }
            )

        model = opts.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        kwargs: dict[str, Any] = {
            "model": model,
            "input": msgs,
            "store": True,
        }
        if tools:
            kwargs["tools"] = tools

        # Call Responses API
        resp = await client.responses.create(**kwargs)
        out = getattr(resp, "output_text", "") or ""

        # Append the assistant message to chat log and return standard result
        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=out)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)


