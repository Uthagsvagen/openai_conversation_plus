# implementera openai conversation enligt google-mönstret (gpt-5 + responses api)

## mål

-   ersätt direktanrop via `AbstractConversationAgent.async_process` med
    en **plattform `conversation`** som exponerar en
    `ConversationEntity`.
-   använd **Home Assistants `ChatLog`** som sanningen för historik och
    verktyg.
-   anropa **OpenAI Responses API** med **GPT-5** och mata in både
    historik och verktyg.
-   returnera resultat via
    `conversation.async_get_result_from_chat_log`.

Källor: konversations-entity + chatlog i HA dev-docs,
`conversation.process` och `conversation_id` i användardocs, hur agent
registreras/avregistreras, Google Generative AI-mönstret i HA, OpenAI
Responses API och kedjning med `previous_response_id`.

------------------------------------------------------------------------

## steg 1 -- uppdatera `manifest.json`

-   lägg till plattformen `conversation`.
-   sätt beroende till `conversation` om du inte redan har det.

``` json
{
  "domain": "openai_conversation_plus",
  "name": "OpenAI Conversation Plus",
  "version": "2025.9.0",
  "dependencies": ["conversation"],

  "codeowners": ["@you"],
  "iot_class": "cloud_polling"
}
```

## steg 2 -- utöka `PLATFORMS` och forwards i `__init__.py`

-   se till att plattformen `conversation` laddas.

``` python
from homeassistant.const import Platform
PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION)

async def async_setup_entry(hass, entry):
    # ... din befintliga klientinit med AsyncOpenAI ...
    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

## steg 3 -- skapa `conversation.py`

-   implementera en `ConversationEntity` som också är en
    `AbstractConversationAgent`.
-   använd `chat_log.async_provide_llm_data(...)` för att ge LLM:et
    HA-verktyg och extra systemprompt.
-   bygg **Responses API-input** av `chat_log.content`.
-   lägg till svaret i `chat_log` och returnera via
    `conversation.async_get_result_from_chat_log`.

``` python
from __future__ import annotations
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from openai import AsyncOpenAI

GPT5_MODEL = "gpt-5"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([OpenAIConversationEntity(entry)])

class OpenAIConversationEntity(conversation.ConversationEntity, conversation.AbstractConversationAgent):
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

    async def _async_handle_message(self, user_input: conversation.ConversationInput, chat_log: conversation.ChatLog) -> conversation.ConversationResult:
        opts = self.entry.options
        client: AsyncOpenAI = self.entry.runtime_data

        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                opts.get("llm_hass_api"),
                opts.get("prompt"),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = []
            for t in chat_log.llm_api.tools:
                tools.append({"type": "function", "name": t.name, "description": getattr(t, "description", ""), "parameters": getattr(t, "parameters", {})})

        msgs = []
        for c in chat_log.content:
            role = "user" if getattr(c, "is_user", False) else "assistant"
            text = getattr(c, "content", "") or ""
            msgs.append({"type": "message", "role": role, "content": [{"type": "input_text", "text": text}]})

        kwargs = {"model": GPT5_MODEL, "input": msgs, "store": True}
        if tools:
            kwargs["tools"] = tools

        resp = await client.responses.create(**kwargs)
        out = getattr(resp, "output_text", "") or ""

        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=out)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)
```

## steg 4 -- valfri kedjning med `previous_response_id`

Om du även vill låta OpenAI bära en kedja parallellt (för t.ex.
server-side minne), lagra `resp.id` per `chat_log.conversation_id` och
skicka in `previous_response_id` nästa gång.

``` python
class OpenAIConversationEntity(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    _last_ids: dict[str, str] = {}

    async def _async_handle_message(self, user_input, chat_log):
        client: AsyncOpenAI = self.entry.runtime_data
        prev = self._last_ids.get(chat_log.conversation_id)
        msgs = [{"type": "message", "role": ("user" if getattr(c, "is_user", False) else "assistant"), "content": [{"type": "input_text", "text": getattr(c, "content", "") or ""}]} for c in chat_log.content]
        kwargs = {"model": GPT5_MODEL, "input": msgs, "store": True}
        if prev:
            kwargs["previous_response_id"] = prev
        resp = await client.responses.create(**kwargs)
        self._last_ids[chat_log.conversation_id] = getattr(resp, "id", "")
        out = getattr(resp, "output_text", "") or ""
        chat_log.async_add_assistant_content_without_tools(AssistantContent(agent_id=user_input.agent_id, content=out))
        return conversation.async_get_result_from_chat_log(user_input, chat_log)
```

## steg 5 -- test via `conversation.process`

-   skicka ett första anrop och spara `conversation_id` från svaret.
-   skicka nästa anrop med samma `conversation_id` och verifiera
    kontext.

## steg 6 -- verktyg (llm api) → responses api

-   `ChatLog` exponerar verktyg via `chat_log.llm_api.tools`; formatera
    dem till Responses API:s funktionstools.

## steg 7 -- streaming (valfritt senare)

-   om du vill streama, använd
    `chat_log.async_add_delta_content_stream(...)` och koppla en
    asyncgenerator som matar textdelar från Responses-streamen.

------------------------------------------------------------------------

## checklist för cursor-agenten

1.  uppdatera `manifest.json` och `__init__.py` enligt steg 1--2.\
2.  skapa filen `conversation.py` med koden i steg 3.\
3.  kör HA, lägg till integrationen, välj GPT-5 modellnamn om det
    konfigureras, annars använd hårdkodad `"gpt-5.1"`.\
4.  prova två turer via `conversation.process`, bekräfta att historiken
    fortsätter.\
5.  aktivera valfri kedjning med `previous_response_id` om du vill
    kombinera HA-historik med server-side kedja.

------------------------------------------------------------------------
