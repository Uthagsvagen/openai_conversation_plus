from __future__ import annotations

from typing import Any, Literal
import json
import logging

from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import (
    async_should_expose,
)
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import entity_registry as er, template

from openai import AsyncOpenAI

from .const import (
    DOMAIN,
    CONF_CHAT_MODEL,
    DEFAULT_CHAT_MODEL,
    CONF_STORE_CONVERSATIONS,
    DEFAULT_STORE_CONVERSATIONS,
    INTEGRATION_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([OpenAIConversationEntity(entry)])


class OpenAIConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    # Enable streaming per HA pattern; we'll stream deltas when possible
    _attr_supports_streaming = True

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
            # Render the prompt template without entities
            rendered_prompt = template.Template(
                (opts.get("prompt") or ""),
                self.hass,
            ).async_render(
                {
                    "ha_name": self.hass.config.location_name or "Home",
                    "current_device_id": getattr(user_input, "device_id", None),
                },
                parse_result=False,
                strict=False,
            )
            
            # For new conversations (empty chat log), append entities directly
            # This avoids template size limits and ensures entities are always included
            is_new_conversation = len(chat_log.content) == 0
            if is_new_conversation:
                exposed = self._get_exposed_entities()
                if exposed:
                    import json
                    entities_json = json.dumps(exposed, ensure_ascii=False)
                    rendered_prompt = f"{rendered_prompt}\n\nAvailable entities:\n{entities_json}"
                    _LOGGER.debug(
                        "[v%s] Appended %d entities to conversation system prompt",
                        INTEGRATION_VERSION,
                        len(exposed)
                    )
            
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                opts.get("llm_hass_api"),
                rendered_prompt,
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        # Convert HA LLM API tools to Responses API tools
        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = []
            for t in chat_log.llm_api.tools:
                # Use nested structure (Chat Completions style) which Responses API also accepts
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": getattr(t, "description", ""),
                            "parameters": getattr(t, "parameters", {}),
                        }
                    }
                )
        
        # Add MCP servers as tools
        from . import build_mcp_tools_from_options
        mcp_tools = build_mcp_tools_from_options(opts)
        if mcp_tools:
            if tools is None:
                tools = []
            tools.extend(mcp_tools)

        # Build Responses API input from chat log
        msgs: list[dict[str, Any]] = []
        for c in chat_log.content:
            is_user = getattr(c, "is_user", False)
            role = "user" if is_user else "assistant"
            text = getattr(c, "content", "") or ""
            # Use input_text for user messages, output_text for assistant messages
            content_type = "input_text" if is_user else "output_text"
            msgs.append(
                {
                    "type": "message",
                    "role": role,
                    "content": [
                        {
                            "type": content_type,
                            "text": text,
                        }
                    ],
                }
            )

        model = opts.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        kwargs: dict[str, Any] = {
            "model": model,
            "input": msgs,
            "store": opts.get(CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Prefer streaming; fall back to non-streaming on error
        try:
            # Create a delta stream in the chat log
            stream_obj = getattr(chat_log, "async_add_delta_content_stream", None)
            if callable(stream_obj):
                delta_stream = chat_log.async_add_delta_content_stream(
                    AssistantContent(agent_id=user_input.agent_id, content="")
                )
                try:
                    # OpenAI Responses streaming
                    stream_ctx = getattr(client.responses, "stream", None)
                    if stream_ctx is None:
                        raise RuntimeError("Responses streaming not available")

                    async with client.responses.stream(**kwargs) as resp_stream:
                        async for event in resp_stream:
                            etype = getattr(event, "type", "")
                            if etype.endswith("output_text.delta"):
                                delta = getattr(event, "delta", None)
                                if delta:
                                    # Push delta into HA stream API
                                    push = getattr(delta_stream, "async_push_delta", None)
                                    if callable(push):
                                        await delta_stream.async_push_delta(delta)
                    # Final response
                    final = await resp_stream.get_final_response()
                    out = getattr(final, "output_text", "") or ""
                finally:
                    # Ensure stream is closed
                    close = getattr(delta_stream, "async_end", None)
                    if callable(close):
                        await delta_stream.async_end()
            else:
                raise RuntimeError("ChatLog delta stream not available")
        except Exception:
            # Non-streaming fallback
            final = await client.responses.create(**kwargs)
            out = getattr(final, "output_text", "") or ""

        # If the model returned a JSON function call in text, normalize and execute
        if out and out.strip().startswith("{") and out.strip().endswith("}"):
            try:
                payload = json.loads(out)
                normalized = None
                if isinstance(payload, dict) and payload.get("type") == "execute_services" and isinstance(payload.get("calls"), list):
                    norm = {"execute_services": {"list": []}}
                    for c in payload["calls"]:
                        item = {
                            "domain": c.get("domain"),
                            "service": c.get("service"),
                        }
                        tgt = c.get("target") or {}
                        if "entity_id" in tgt:
                            item["target"] = {"entity_id": tgt["entity_id"]}
                        elif "area_name" in tgt:
                            item["target"] = {"area_name": tgt["area_name"]}
                        elif "area" in tgt:
                            item["target"] = {"area_name": tgt["area"]}
                        elif "device_id" in tgt:
                            item["target"] = {"device_id": tgt["device_id"]}
                        data = c.get("service_data") or c.get("data") or {}
                        if data:
                            item["service_data"] = data
                        norm["execute_services"]["list"].append(item)
                    normalized = norm
                else:
                    normalized = payload

                if isinstance(normalized, dict) and "execute_services" in normalized:
                    _LOGGER.info("[v%s] Detected JSON function call in conversation output; executing", INTEGRATION_VERSION)
                    from .helpers import get_function_executor
                    function_executor = get_function_executor("native")
                    fn_config = {"type": "native", "name": "execute_service"}
                    try:
                        await function_executor.execute(
                            self.hass,
                            fn_config,
                            normalized["execute_services"],
                            user_input,
                            [],
                        )
                        out = "Utfört."
                    except Exception as e:  # noqa: BLE001
                        _LOGGER.error("[v%s] Failed to execute normalized function call: %s", INTEGRATION_VERSION, e)
                        out = f"Fel vid exekvering: {e}"
            except Exception:
                # Not JSON or parsing failed; keep original out
                pass

        # Append the assistant message (final text) and return
        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=out)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    def _get_exposed_entities(self) -> list[dict[str, Any]]:
        try:
            entry_id = getattr(self.entry, "entry_id", None)
            all_states = self.hass.states.async_all()
            states = [
                s for s in all_states if async_should_expose(self.hass, entry_id, s.entity_id)
            ]
            if not states:
                _LOGGER.info(
                    "[v%s] No entities exposed for conversation agent; falling back to all (%d)",
                    INTEGRATION_VERSION,
                    len(all_states),
                )
                states = all_states
            reg = er.async_get(self.hass)
            out: list[dict[str, Any]] = []
            for s in states:
                try:
                    entity = reg.async_get(s.entity_id)
                    aliases = list(getattr(entity, "aliases", []) or []) if entity else []
                    cur = self.hass.states.get(s.entity_id)
                    out.append(
                        {
                            "entity_id": s.entity_id,
                            "name": getattr(s, "name", s.entity_id) or s.entity_id,
                            "state": (cur.state if cur else "unavailable"),
                            "aliases": aliases,
                        }
                    )
                except Exception:  # noqa: BLE001
                    continue
            _LOGGER.info(
                "[v%s] Exposed entities prepared for conversation: %d / %d",
                INTEGRATION_VERSION,
                len(states),
                len(all_states),
            )
            return out
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("[v%s] Failed to build exposed entities for conversation: %s", INTEGRATION_VERSION, err)
            return []


