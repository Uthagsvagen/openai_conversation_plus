"""The OpenAI Conversation integration."""

from __future__ import annotations

import json
import logging
import time
from typing import Literal
from types import SimpleNamespace

import yaml
from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import intent, template
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid
from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai._exceptions import AuthenticationError, OpenAIError
from openai.types.chat.chat_completion import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
)

from .const import (
    CONF_API_VERSION,
    CONF_ATTACH_USERNAME,
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CONTEXT_THRESHOLD,
    CONF_CONTEXT_TRUNCATE_STRATEGY,
    CONF_ENABLE_CONVERSATION_EVENTS,
    CONF_ENABLE_WEB_SEARCH,
    CONF_FUNCTIONS,
    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    CONF_MAX_TOKENS,
    CONF_ORGANIZATION,
    CONF_PROMPT,
    CONF_REASONING_LEVEL,
    CONF_SEARCH_CONTEXT_SIZE,
    CONF_SKIP_AUTHENTICATION,
    CONF_STORE_CONVERSATIONS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_USE_TOOLS,
    CONF_USER_LOCATION,
    CONF_VERBOSITY,
    DEFAULT_ATTACH_USERNAME,
    DEFAULT_CHAT_MODEL,
    DEFAULT_CONF_BASE_URL,
    DEFAULT_CONF_FUNCTIONS,
    DEFAULT_CONTEXT_THRESHOLD,
    DEFAULT_CONTEXT_TRUNCATE_STRATEGY,
    DEFAULT_ENABLE_CONVERSATION_EVENTS,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    DEFAULT_MAX_TOKENS,
    DEFAULT_NAME,
    DEFAULT_PROMPT,
    DEFAULT_REASONING_LEVEL,
    DEFAULT_SEARCH_CONTEXT_SIZE,
    DEFAULT_SKIP_AUTHENTICATION,
    DEFAULT_STORE_CONVERSATIONS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_USE_TOOLS,
    DEFAULT_USER_LOCATION,
    DEFAULT_VERBOSITY,
    DOMAIN,
    EVENT_CONVERSATION_FINISHED,
    GPT5_MODELS,
)
from .exceptions import (
    FunctionLoadFailed,
    FunctionNotFound,
    InvalidFunction,
    ParseArgumentsFailed,
    TokenLengthExceededError,
)
from .helpers import get_function_executor, is_azure
from . import helpers
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = ["ai_task"]
DATA_AGENT = "agent"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    try:
        import openai
        _LOGGER.info(
            "OpenAI Conversation Plus: Loaded OpenAI Python library version: %s",
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.warning("OpenAI Conversation Plus: OpenAI library not available")

    hass.data.setdefault(DOMAIN, {})
    await async_setup_services(hass, config)

    try:
        import openai
        _LOGGER.info(
            "OpenAI Conversation Plus: openai library version %s",
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.info("OpenAI Conversation Plus: openai library version unknown")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        import openai
        _LOGGER.info(
            "OpenAI Conversation Plus: Setting up entry with OpenAI library version: %s",
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.warning(
            "OpenAI Conversation Plus: OpenAI library not available during entry setup"
        )

    try:
        await helpers.validate_authentication(
            hass=hass,
            api_key=entry.data[CONF_API_KEY],
            base_url=entry.data.get(CONF_BASE_URL),
            api_version=entry.data.get(CONF_API_VERSION),
            organization=entry.data.get(CONF_ORGANIZATION),
            skip_authentication=entry.data.get(
                CONF_SKIP_AUTHENTICATION, DEFAULT_SKIP_AUTHENTICATION
            ),
        )
    except AuthenticationError as err:
        _LOGGER.error("Invalid API key: %s", err)
        return False
    except OpenAIError as err:
        raise ConfigEntryNotReady(err) from err
    except Exception as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False

    agent = OpenAIAgent(hass, entry)

    data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    data[CONF_API_KEY] = entry.data[CONF_API_KEY]
    data[DATA_AGENT] = agent

    conversation.async_set_agent(hass, entry, agent)

    try:
        from homeassistant.config_entries import ConfigEntryState
        if hasattr(entry, "mock_state"):
            entry.mock_state(hass, ConfigEntryState.LOADED)  # type: ignore[arg-type]
        elif hasattr(entry, "_async_set_state"):
            entry._async_set_state(hass, ConfigEntryState.LOADED)  # type: ignore[attr-defined]
        else:
            entry.state = ConfigEntryState.LOADED
    except Exception:
        pass

    try:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        )
    except Exception:
        _LOGGER.debug("Deferred platform forwarding")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        try:
            hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        except Exception:
            pass
        conversation.async_unset_agent(hass, entry)
    return unload_ok


class OpenAIAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        base_url = entry.data.get(CONF_BASE_URL)
        if is_azure(base_url):
            self.client = AsyncAzureOpenAI(
                api_key=entry.data[CONF_API_KEY],
                azure_endpoint=base_url,
                api_version=entry.data.get(CONF_API_VERSION),
                organization=entry.data.get(CONF_ORGANIZATION),
                http_client=get_async_client(hass),
            )
        else:
            self.client = AsyncOpenAI(
                api_key=entry.data[CONF_API_KEY],
                base_url=base_url,
                organization=entry.data.get(CONF_ORGANIZATION),
                http_client=get_async_client(hass),
            )
        _ = hass.async_add_executor_job(self.client.platform_headers)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        _LOGGER.debug("Processing user input: %s", user_input.text)
        exposed_entities = self.get_exposed_entities()

        if user_input.conversation_id in self.history:
            conversation_id = user_input.conversation_id
            messages = self.history[conversation_id]
        else:
            conversation_id = ulid.ulid()
            user_input.conversation_id = conversation_id
            try:
                system_message = self._generate_system_message(
                    exposed_entities, user_input
                )
            except TemplateError as err:
                _LOGGER.error("Error rendering prompt: %s", err)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Sorry, I had a problem with my template: {err}",
                )
                return conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )
            messages = [system_message]
        user_message = {"role": "user", "content": user_input.text}
        if self.entry.options.get(CONF_ATTACH_USERNAME, DEFAULT_ATTACH_USERNAME):
            user = user_input.context.user_id
            if user is not None:
                user_message[ATTR_NAME] = user

        messages.append(user_message)

        try:
            query_response = await self.query(user_input, messages, exposed_entities, 0)
        except OpenAIError as err:
            _LOGGER.error("OpenAI API error: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem talking to OpenAI: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )
        except HomeAssistantError as err:
            _LOGGER.error("Home Assistant error: %s", err, exc_info=err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Something went wrong: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )
        except Exception as err:
            _LOGGER.error(
                "Unexpected error during intent recognition: %s", err, exc_info=True
            )
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                "Unexpected error during intent recognition",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        message_dict = {
            "role": getattr(query_response.message, "role", "assistant"),
            "content": query_response.message.content or "",
        }
        if (
            hasattr(query_response.message, "function_call")
            and query_response.message.function_call
        ):
            message_dict["function_call"] = {
                "name": query_response.message.function_call.name,
                "arguments": query_response.message.function_call.arguments,
            }
        if (
            hasattr(query_response.message, "tool_calls")
            and query_response.message.tool_calls
        ):
            message_dict["tool_calls"] = [
                {
                    "id": tool.id,
                    "type": tool.type,
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments,
                    },
                }
                for tool in query_response.message.tool_calls
            ]

        messages.append(message_dict)
        self.history[conversation_id] = messages

        if self.entry.options.get(
            CONF_ENABLE_CONVERSATION_EVENTS, DEFAULT_ENABLE_CONVERSATION_EVENTS
        ):
            self.hass.bus.async_fire(
                EVENT_CONVERSATION_FINISHED,
                {
                    "response": {
                        "id": getattr(query_response.response, "id", None),
                        "model": getattr(query_response.response, "model", None),
                        "usage": getattr(query_response.response, "usage", None),
                    },
                    "conversation_id": conversation_id,
                    "user_input_length": len(user_input.text) if user_input.text else 0,
                    "response_length": len(query_response.message.content)
                    if query_response.message.content
                    else 0,
                    "message_count": len(messages),
                    "timestamp": time.time(),
                },
            )

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(query_response.message.content)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _generate_system_message(
        self, exposed_entities, user_input: conversation.ConversationInput
    ):
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        prompt = self._async_generate_prompt(raw_prompt, exposed_entities, user_input)
        return {"role": "system", "content": prompt}

    def _async_generate_prompt(
        self,
        raw_prompt: str,
        exposed_entities,
        user_input: conversation.ConversationInput,
    ) -> str:
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
                "exposed_entities": exposed_entities,
                "current_device_id": user_input.device_id,
            },
            parse_result=False,
        )

    def get_exposed_entities(self):
        states = [
            state
            for state in self.hass.states.async_all()
            if async_should_expose(self.hass, conversation.DOMAIN, state.entity_id)
        ]
        entity_registry = er.async_get(self.hass)
        exposed_entities = []
        for state in states:
            entity_id = state.entity_id
            entity = entity_registry.async_get(entity_id)
            aliases = []
            if entity and entity.aliases:
                aliases = entity.aliases
            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                }
            )
        return exposed_entities

    def get_functions(self):
        try:
            function = self.entry.options.get(CONF_FUNCTIONS)
            result = yaml.safe_load(function) if function else DEFAULT_CONF_FUNCTIONS
            if result:
                for setting in result:
                    function_executor = get_function_executor(
                        setting["function"]["type"]
                    )
                    setting["function"] = function_executor.to_arguments(
                        setting["function"]
                    )
            return result
        except (InvalidFunction, FunctionNotFound) as e:
            raise e
        except Exception as err:
            raise FunctionLoadFailed() from err

    async def truncate_message_history(
        self, messages, exposed_entities, user_input: conversation.ConversationInput
    ):
        strategy = self.entry.options.get(
            CONF_CONTEXT_TRUNCATE_STRATEGY, DEFAULT_CONTEXT_TRUNCATE_STRATEGY
        )
        if strategy == "clear":
            last_user_message_index = None
            for i in reversed(range(len(messages))):
                if messages[i]["role"] == "user":
                    last_user_message_index = i
                    break
            if last_user_message_index is not None:
                del messages[1:last_user_message_index]
                messages[0] = self._generate_system_message(
                    exposed_entities, user_input
                )

    async def query(
        self,
        user_input: conversation.ConversationInput,
        messages,
        exposed_entities,
        n_requests,
    ) -> "OpenAIQueryResponse":
        model = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        max_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TOP_P)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        use_tools = self.entry.options.get(CONF_USE_TOOLS, DEFAULT_USE_TOOLS)
        context_threshold = self.entry.options.get(
            CONF_CONTEXT_THRESHOLD, DEFAULT_CONTEXT_THRESHOLD
        )
        functions = [setting["spec"] for setting in (self.get_functions() or [])]
        # Validate that all functions have required fields
        valid_functions = []
        for func in functions:
            if func and "name" in func:
                valid_functions.append(func)
            else:
                _LOGGER.warning("Skipping function without name: %s", func)
        functions = valid_functions
        
        function_call = "auto"
        if n_requests == self.entry.options.get(
            CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
            DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
        ):
            function_call = "none"

        tool_kwargs = {"functions": functions, "function_call": function_call}
        if use_tools:
            tool_kwargs = {
                "tools": [{"type": "function", "function": func} for func in functions],
                "tool_choice": function_call,
            }
        if len(functions) == 0:
            tool_kwargs = {}

        reasoning_level = self.entry.options.get(
            CONF_REASONING_LEVEL, DEFAULT_REASONING_LEVEL
        )
        verbosity = self.entry.options.get(CONF_VERBOSITY, DEFAULT_VERBOSITY)

        api_tools = []
        if tool_kwargs.get("tools"):
            api_tools.extend(tool_kwargs["tools"])

        if self.entry.options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH):
            web_search_tool = {
                "type": "web_search",
                "search_context_size": self.entry.options.get(
                    CONF_SEARCH_CONTEXT_SIZE, DEFAULT_SEARCH_CONTEXT_SIZE
                ),
            }
            user_location = self.entry.options.get(
                CONF_USER_LOCATION, DEFAULT_USER_LOCATION
            )
            if user_location and any(user_location.values()):
                web_search_tool["user_location"] = {
                    "type": "approximate",
                    "country": user_location.get("country", ""),
                    "city": user_location.get("city", ""),
                    "region": user_location.get("region", ""),
                }
            api_tools.append(web_search_tool)

        previous_response_id = None
        if hasattr(user_input, "agent_response_id"):
            previous_response_id = user_input.agent_response_id

        response_kwargs = {
            "model": model,
            "input": messages,
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "store": self.entry.options.get(
                CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS
            ),
        }

        if model in GPT5_MODELS:
            response_kwargs["reasoning"] = {"effort": reasoning_level}
            if verbosity:
                response_kwargs["text"] = {"verbosity": verbosity}
            response_kwargs["response_format"] = {"type": "text"}

        if api_tools:
            response_kwargs["tools"] = api_tools
            response_kwargs["tool_choice"] = tool_kwargs.get("tool_choice", "auto")

        if previous_response_id:
            response_kwargs["previous_response_id"] = previous_response_id

        try:
            response = await self.client.responses.create(**response_kwargs)
        except TypeError:
            response_kwargs.pop("reasoning", None)
            response_kwargs.pop("text", None)
            response_kwargs.pop("response_format", None)
            response = await self.client.responses.create(**response_kwargs)
        except Exception as err:
            _LOGGER.error("Response API error: %s", err)
            raise ConfigEntryNotReady(
                "Response API not available or incompatible OpenAI library version."
            ) from err

        _LOGGER.info("Response API Prompt for %s: %s", model, json.dumps(messages))

        text = getattr(response, "output_text", None)
        if not text and hasattr(response, "choices") and response.choices:
            choice0 = response.choices[0]
            msg = getattr(choice0, "message", None)
            if msg and getattr(msg, "content", None):
                text = msg.content
        if not text and hasattr(response, "output") and response.output:
            try:
                first = response.output[0]
                parts = getattr(first, "content", []) or []
                texts = []
                for p in parts:
                    t = getattr(getattr(p, "text", None), "value", None)
                    if t:
                        texts.append(t)
                text = "\n".join(texts) if texts else None
            except Exception:
                pass

        message = SimpleNamespace(role="assistant", content=text or "")

        if hasattr(response, "id"):
            user_input.agent_response_id = response.id

        if getattr(response, "usage", None) and getattr(
            response.usage, "total_tokens", None
        ):
            try:
                if response.usage.total_tokens > context_threshold:
                    await self.truncate_message_history(
                        messages, exposed_entities, user_input
                    )
            except Exception:
                pass

        return OpenAIQueryResponse(response=response, message=message)

    async def execute_function_call(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
    ) -> "OpenAIQueryResponse":
        function_name = message.function_call.name
        function = next(
            (s for s in self.get_functions() if s["spec"]["name"] == function_name),
            None,
        )
        if function is not None:
            return await self.execute_function(
                user_input,
                messages,
                message,
                exposed_entities,
                n_requests,
                function,
            )
        raise FunctionNotFound(function_name)

    async def execute_function(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
        function,
    ) -> "OpenAIQueryResponse":
        function_executor = get_function_executor(function["function"]["type"])
        try:
            arguments = json.loads(message.function_call.arguments)
        except json.decoder.JSONDecodeError as err:
            raise ParseArgumentsFailed(message.function_call.arguments) from err
        result = await function_executor.execute(
            self.hass, function["function"], arguments, user_input, exposed_entities
        )
        messages.append(
            {
                "role": "function",
                "name": message.function_call.name,
                "content": str(result),
            }
        )
        return await self.query(user_input, messages, exposed_entities, n_requests)

    async def execute_tool_calls(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
    ) -> "OpenAIQueryResponse":
        message_dict = {
            "role": getattr(message, "role", "assistant"),
            "content": message.content or "",
        }
        if hasattr(message, "function_call") and message.function_call:
            message_dict["function_call"] = {
                "name": message.function_call.name,
                "arguments": message.function_call.arguments,
            }
        if hasattr(message, "tool_calls") and message.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tool.id,
                    "type": tool.type,
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments,
                    },
                }
                for tool in message.tool_calls
            ]
        messages.append(message_dict)
        for tool in message.tool_calls:
            function_name = tool.function.name
            function = next(
                (s for s in self.get_functions() if s["spec"]["name"] == function_name),
                None,
            )
            if function is not None:
                result = await self.execute_tool_function(
                    user_input, tool, exposed_entities, function
                )
                messages.append(
                    {
                        "tool_call_id": tool.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(result),
                    }
                )
            else:
                raise FunctionNotFound(function_name)
        return await self.query(user_input, messages, exposed_entities, n_requests)

    async def execute_tool_function(
        self,
        user_input: conversation.ConversationInput,
        tool,
        exposed_entities,
        function,
    ) -> "OpenAIQueryResponse":
        function_executor = get_function_executor(function["function"]["type"])
        try:
            arguments = json.loads(tool.function.arguments)
        except json.decoder.JSONDecodeError as err:
            raise ParseArgumentsFailed(tool.function.arguments) from err
        result = await function_executor.execute(
            self.hass, function["function"], arguments, user_input, exposed_entities
        )
        return result


class OpenAIQueryResponse:
    def __init__(
        self, response: ChatCompletion, message: ChatCompletionMessage
    ) -> None:
        self.response = response
        self.message = message