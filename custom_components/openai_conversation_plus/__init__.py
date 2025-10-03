"""The OpenAI Conversation integration."""

from __future__ import annotations

import json
import logging
import time
from typing import Literal, Any
from types import SimpleNamespace

import yaml
from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_API_KEY, MATCH_ALL, Platform
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
from openai import AsyncOpenAI
from openai._exceptions import AuthenticationError, OpenAIError

from .const import (
    CONF_API_VERSION,
    CONF_ATTACH_USERNAME,
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_ENABLE_CONVERSATION_EVENTS,
    CONF_ENABLE_WEB_SEARCH,
    CONF_FUNCTIONS,
    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    CONF_MAX_TOKENS,
    CONF_MCP_SERVERS,
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
    INTEGRATION_VERSION,
)
from .exceptions import (
    FunctionLoadFailed,
    FunctionNotFound,
    InvalidFunction,
    ParseArgumentsFailed,
    TokenLengthExceededError,
)
from .helpers import get_function_executor
from . import helpers
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

# Version is imported from const.py as INTEGRATION_VERSION

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = ["ai_task", Platform.CONVERSATION]
DATA_AGENT = "agent"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    try:
        import openai
        _LOGGER.info(
            "[v%s] OpenAI Conversation Plus: Loaded OpenAI Python library version: %s",
            INTEGRATION_VERSION,
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.warning("[v%s] OpenAI Conversation Plus: OpenAI library not available", INTEGRATION_VERSION)

    hass.data.setdefault(DOMAIN, {})
    await async_setup_services(hass, config)

    try:
        import openai
        _LOGGER.info(
            "[v%s] OpenAI Conversation Plus: openai library version %s",
            INTEGRATION_VERSION,
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.info("[v%s] OpenAI Conversation Plus: openai library version unknown", INTEGRATION_VERSION)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        import openai
        _LOGGER.info(
            "[v%s] OpenAI Conversation Plus: Setting up entry with OpenAI library version: %s",
            INTEGRATION_VERSION,
            getattr(openai, "__version__", "unknown"),
        )
    except Exception:
        _LOGGER.warning(
            "[v%s] OpenAI Conversation Plus: OpenAI library not available during entry setup",
            INTEGRATION_VERSION
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
        _LOGGER.error("[v%s] Invalid API key: %s", INTEGRATION_VERSION, err)
        return False
    except OpenAIError as err:
        raise ConfigEntryNotReady(err) from err
    except Exception as err:
        _LOGGER.error("[v%s] Authentication failed: %s", INTEGRATION_VERSION, err)
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
        # Store client for conversation platform to access
        entry.runtime_data = agent.client  # type: ignore[attr-defined]
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        )
    except Exception:
        _LOGGER.debug("[v%s] Deferred platform forwarding", INTEGRATION_VERSION)

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


def _normalize_mcp_items(data):
    """Normalize MCP configuration data into a consistent format."""
    if isinstance(data, dict) and "mcpServers" in data:
        items = []
        for label, cfg in data["mcpServers"].items():
            url = None
            key = None
            allowed_tools = None
            require_approval = None
            if isinstance(cfg, dict):
                url = cfg.get("server_url") or cfg.get("url")
                if not url and isinstance(cfg.get("args"), list) and cfg["args"]:
                    url = cfg["args"][0]
                key = cfg.get("server_api_key") or cfg.get("api_key") or cfg.get("env", {}).get("API_ACCESS_TOKEN")
                allowed_tools = cfg.get("allowed_tools")
                require_approval = cfg.get("require_approval")
            items.append({
                "server_label": label,
                "server_url": url,
                "server_api_key": key,
                "allowed_tools": allowed_tools,
                "require_approval": require_approval,
            })
        return items
    if isinstance(data, list):
        return [
            {
                "server_label": it.get("server_label") or it.get("label"),
                "server_url": it.get("server_url") or it.get("url"),
                "server_api_key": it.get("server_api_key") or it.get("api_key"),
                "allowed_tools": it.get("allowed_tools"),
                "require_approval": it.get("require_approval"),
            }
            for it in data if isinstance(it, dict)
        ]
    return []


def build_mcp_tools_from_options(options):
    """Build MCP tools from integration options."""
    raw = options.get(CONF_MCP_SERVERS) or ""
    try:
        data = yaml.safe_load(raw) if raw.strip() else None
    except Exception:
        return []
    items = _normalize_mcp_items(data) if data else []
    tools = []
    for it in items:
        if it.get("server_label") and it.get("server_url"):
            tool = {
                "type": "mcp",
                "server_label": it["server_label"],
                "server_url": it["server_url"],
                "require_approval": it.get("require_approval", "never"),
            }
            if it.get("server_api_key"):
                tool["server_api_key"] = it["server_api_key"]
            # Add allowed_tools if specified
            if it.get("allowed_tools"):
                # Support both list and comma-separated string
                allowed = it["allowed_tools"]
                if isinstance(allowed, str):
                    tool["allowed_tools"] = [t.strip() for t in allowed.split(",")]
                elif isinstance(allowed, list):
                    tool["allowed_tools"] = allowed
            tools.append(tool)
    return tools


def get_functions_from_options(options: dict) -> list[dict]:
    """Get function definitions from integration options."""
    try:
        function = options.get(CONF_FUNCTIONS)
        result = yaml.safe_load(function) if function else DEFAULT_CONF_FUNCTIONS
        if result:
            for setting in result:
                function_executor = get_function_executor(
                    setting["function"]["type"]
                )
                setting["function"] = function_executor.to_arguments(
                    setting["function"]
                )
        return result or []
    except Exception as err:
        _LOGGER.warning("[v%s] Failed to load functions: %s", INTEGRATION_VERSION, err)
        return []


class OpenAIAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        # Track last response id per conversation to enable previous_response_id without mutating ConversationInput
        self._last_response_ids: dict[str, str] = {}
        base_url = entry.data.get(CONF_BASE_URL)
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
        _LOGGER.debug("[v%s] Processing user input: %s", INTEGRATION_VERSION, user_input.text)
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
                _LOGGER.error("[v%s] Error rendering prompt: %s", INTEGRATION_VERSION, err)
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
            _LOGGER.error("[v%s] OpenAI API error: %s", INTEGRATION_VERSION, err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem talking to OpenAI: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )
        except HomeAssistantError as err:
            _LOGGER.error("[v%s] Home Assistant error: %s", INTEGRATION_VERSION, err, exc_info=err)
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
                "[v%s] Unexpected error during intent recognition: %s", INTEGRATION_VERSION, err, exc_info=True
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
            # Ensure usage is JSON serializable
            usage = getattr(query_response.response, "usage", None)
            if usage is not None:
                try:
                    if hasattr(usage, "model_dump"):
                        usage = usage.model_dump()
                    elif hasattr(usage, "to_dict"):
                        usage = usage.to_dict()
                    else:
                        import json as _json
                        usage = _json.loads(_json.dumps(usage, default=str))
                except Exception:
                    usage = str(usage)

            self.hass.bus.async_fire(
                EVENT_CONVERSATION_FINISHED,
                {
                    "response": {
                        "id": getattr(query_response.response, "id", None),
                        "model": getattr(query_response.response, "model", None),
                        "usage": usage,
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
        prompt = self._async_generate_prompt(raw_prompt, user_input)
        
        # Append entities directly to the system message (not via template)
        if exposed_entities:
            entities_json = json.dumps(exposed_entities, ensure_ascii=False)
            prompt = f"{prompt}\n\nAvailable entities:\n{entities_json}"
            _LOGGER.debug(
                "[v%s] Appended %d entities to system prompt",
                INTEGRATION_VERSION,
                len(exposed_entities)
            )
        
        return {"role": "system", "content": prompt}

    def _async_generate_prompt(
        self,
        raw_prompt: str,
        user_input: conversation.ConversationInput,
    ) -> str:
        """Generate prompt with error handling for missing template variables."""
        try:
            # Provide safe defaults for template variables (entities now handled separately)
            template_vars = {
                "ha_name": self.hass.config.location_name or "Home",
                "current_device_id": user_input.device_id if user_input and user_input.device_id else None,
            }
            # Render template with error handling
            return template.Template(raw_prompt, self.hass).async_render(
                template_vars,
                parse_result=False,
                strict=False,  # Don't fail on undefined variables
            )
        except TemplateError as err:
            _LOGGER.warning(
                "[v%s] Template rendering warning (continuing anyway): %s",
                INTEGRATION_VERSION,
                err,
            )
            # Return a basic prompt if template fails
            return raw_prompt.replace("{{", "").replace("}}", "").replace("{%", "").replace("%}", "")

    def get_exposed_entities(self):
        """Get exposed entities with error handling for missing or unavailable entities."""
        try:
            # Use this agent's entry_id when checking exposure; using conversation.DOMAIN would
            # mark everything as not exposed for this specific agent instance.
            entry_id = getattr(self.entry, "entry_id", None)
            all_states = self.hass.states.async_all()
            states = [
                state
                for state in all_states
                if async_should_expose(self.hass, entry_id, state.entity_id)
            ]
            if not states:
                _LOGGER.info(
                    "[v%s] No entities exposed for this agent; falling back to all states (%d)",
                    INTEGRATION_VERSION,
                    len(all_states),
                )
                states = all_states
            entity_registry = er.async_get(self.hass)
            exposed_entities = []
            for state in states:
                try:
                    entity_id = state.entity_id
                    entity = entity_registry.async_get(entity_id)
                    aliases = []
                    if entity and entity.aliases:
                        aliases = entity.aliases
                    # Get state safely
                    current_state = self.hass.states.get(entity_id)
                    state_value = current_state.state if current_state else "unavailable"
                    exposed_entities.append(
                        {
                            "entity_id": entity_id,
                            "name": state.name if hasattr(state, 'name') else entity_id,
                            "state": state_value,
                            "aliases": aliases,
                        }
                    )
                except Exception as err:
                    _LOGGER.debug(
                        "[v%s] Skipping entity %s due to error: %s",
                        INTEGRATION_VERSION,
                        state.entity_id if hasattr(state, 'entity_id') else 'unknown',
                        err,
                    )
                    continue
            return exposed_entities
        except Exception as err:
            _LOGGER.warning(
                "[v%s] Error getting exposed entities (returning empty list): %s",
                INTEGRATION_VERSION,
                err,
            )
            return []

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
        # Truncation logic removed in favor of Home Assistant ChatLog history
        return

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
        # Truncation threshold removed (ChatLog controls history)
        
        _LOGGER.info("[v%s] Loading functions... use_tools=%s", INTEGRATION_VERSION, use_tools)
        functions = [setting["spec"] for setting in (self.get_functions() or [])]
        _LOGGER.info("[v%s] Loaded %d functions from configuration", INTEGRATION_VERSION, len(functions))
        
        # Validate that all functions have required fields
        valid_functions = []
        for func in functions:
            if func and "name" in func:
                valid_functions.append(func)
                _LOGGER.debug("[v%s] Valid function: %s", INTEGRATION_VERSION, func.get("name"))
            else:
                _LOGGER.warning("[v%s] Skipping function without name: %s", INTEGRATION_VERSION, func)
        functions = valid_functions
        
        # Debug log the functions structure
        _LOGGER.info("[v%s] Final function count: %d valid functions ready for tool execution", INTEGRATION_VERSION, len(functions))
        _LOGGER.debug("[v%s] Functions to be used: %s", INTEGRATION_VERSION, json.dumps(functions))
        
        function_call = "auto"
        if n_requests == self.entry.options.get(
            CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
            DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
        ):
            function_call = "none"

        # Build Responses API-native tools list
        responses_function_tools = []
        if not use_tools:
            _LOGGER.warning("[v%s] Tools/functions are DISABLED in configuration (use_tools=%s) - Model will not be able to control devices!", INTEGRATION_VERSION, use_tools)
        elif not functions:
            _LOGGER.warning("[v%s] No functions configured - Model will not be able to control devices!", INTEGRATION_VERSION)
        else:
            _LOGGER.info("[v%s] Building tools from %d functions for tool execution", INTEGRATION_VERSION, len(functions))
        
        if use_tools and functions:
            for func in functions:
                # Try the Chat Completions-style structure with nested function object
                # This is the format that Chat Completions uses, and Responses API might expect the same
                tool = {
                    "type": "function",
                    "function": {
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "parameters": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                }
                _LOGGER.debug("[v%s] Built function tool with nested structure: %s", INTEGRATION_VERSION, json.dumps(tool))
                responses_function_tools.append(tool)

        reasoning_level = self.entry.options.get(
            CONF_REASONING_LEVEL, DEFAULT_REASONING_LEVEL
        )
        verbosity = self.entry.options.get(CONF_VERBOSITY, DEFAULT_VERBOSITY)

        api_tools = []
        if responses_function_tools:
            _LOGGER.debug("[v%s] Adding %d function tools to api_tools", INTEGRATION_VERSION, len(responses_function_tools))
            # Ensure list type
            if isinstance(responses_function_tools, list):
                api_tools.extend(responses_function_tools)
            else:
                _LOGGER.warning(
                    "[v%s] responses_function_tools is not a list: %s",
                    INTEGRATION_VERSION,
                    type(responses_function_tools),
                )

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

        # Add MCP servers as tools
        mcp_tools = build_mcp_tools_from_options(self.entry.options)
        if mcp_tools:
            api_tools.extend(mcp_tools)
            _LOGGER.debug(
                "[v%s] Added %d MCP tools", INTEGRATION_VERSION, len(mcp_tools)
            )

        previous_response_id = None
        try:
            conversation_id_for_previous = getattr(user_input, "conversation_id", None)
        except Exception:
            conversation_id_for_previous = None
        if conversation_id_for_previous:
            previous_response_id = self._last_response_ids.get(conversation_id_for_previous)

        response_kwargs = {
            "model": model,
            "input": messages,
            "max_output_tokens": max_tokens,
            "parallel_tool_calls": True,  # Enable parallel tool execution
            "stream": True,  # Enable streaming responses
            "store": self.entry.options.get(
                CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS
            ),
        }
        
        # Note: temperature and top_p are NOT supported by the Responses API
        # The API only supports reasoning.effort and text.verbosity for GPT-5
        if temperature != DEFAULT_TEMPERATURE or top_p != DEFAULT_TOP_P:
            _LOGGER.info(
                "[v%s] Note: temperature and top_p are not used with Responses API. "
                "Use reasoning_level and verbosity instead for GPT-5 models.",
                INTEGRATION_VERSION
            )

        if model in GPT5_MODELS:
            response_kwargs["reasoning"] = {"effort": reasoning_level}
            if verbosity:
                # Map legacy verbosity values to supported ones
                from .const import VERBOSITY_COMPAT_MAP
                mapped_verbosity = VERBOSITY_COMPAT_MAP.get(verbosity, verbosity)
                response_kwargs["text"] = {
                    "verbosity": mapped_verbosity,
                    "format": {"type": "text"}
                }

        if api_tools:
            # Validate tools structure for Responses API
            validated_tools = []
            for tool in api_tools:
                tool_type = tool.get("type")
                if tool_type == "function":
                    # Check for nested function structure (Chat Completions style)
                    if "function" in tool and tool["function"].get("name"):
                        validated_tools.append(tool)
                    # Also support flat structure for backward compatibility
                    elif tool.get("name"):
                        # Convert flat structure to nested for consistency
                        nested_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.get("name"),
                                "description": tool.get("description", ""),
                                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                            }
                        }
                        validated_tools.append(nested_tool)
                    else:
                        _LOGGER.warning(
                            "[v%s] Skipping function tool without name: %s",
                            INTEGRATION_VERSION,
                            tool,
                        )
                elif tool_type == "web_search":
                    # Keep as-is; supported by Responses API
                    validated_tools.append(tool)
                elif tool_type == "mcp":
                    # MCP tool must have server_label, server_url, and require_approval
                    if tool.get("server_label") and tool.get("server_url"):
                        # Ensure require_approval is set (default to "never" if missing)
                        if "require_approval" not in tool:
                            tool["require_approval"] = "never"
                        validated_tools.append(tool)
                    else:
                        _LOGGER.warning(
                            "[v%s] Skipping MCP tool without required fields (server_label, server_url): %s",
                            INTEGRATION_VERSION,
                            tool,
                        )
                else:
                    _LOGGER.warning(
                        "[v%s] Unknown tool type: %s",
                        INTEGRATION_VERSION,
                        tool_type,
                    )

            if validated_tools:
                _LOGGER.debug(
                    "[v%s] API tools being sent: %s",
                    INTEGRATION_VERSION,
                    json.dumps(validated_tools),
                )
                response_kwargs["tools"] = validated_tools
                # Keep tool_choice as "auto" - let the model decide when to use tools
                # The prompt instructions should be enough to guide tool usage
                response_kwargs["tool_choice"] = function_call
                _LOGGER.info("[v%s] Setting tool_choice to '%s' for tool execution", INTEGRATION_VERSION, function_call)
                
                # IMPORTANT: Disable streaming when tools are present
                # Responses API may not support streaming with tool calls
                response_kwargs["stream"] = False
                _LOGGER.info(
                    "[v%s] Disabled streaming for tool call request (tools: %d, tool_choice: %s)",
                    INTEGRATION_VERSION,
                    len(validated_tools),
                    function_call
                )

        if previous_response_id:
            response_kwargs["previous_response_id"] = previous_response_id

        # Enhanced logging before API call
        _LOGGER.info(
            "[v%s] Sending to Responses API - Model: %s, Tools: %d, tool_choice: %s, stream: %s, use_tools: %s",
            INTEGRATION_VERSION,
            model,
            len(response_kwargs.get("tools", [])),
            response_kwargs.get("tool_choice", "none"),
            response_kwargs.get("stream", False),
            use_tools
        )
        _LOGGER.debug("[v%s] Full response_kwargs being sent to API: %s", INTEGRATION_VERSION, json.dumps(response_kwargs))

        try:
            response = await self.client.responses.create(**response_kwargs)
        except TypeError as e:
            _LOGGER.warning("[v%s] TypeError in responses.create, removing incompatible parameters: %s", INTEGRATION_VERSION, e)
            response_kwargs.pop("reasoning", None)
            response_kwargs.pop("text", None)
            response_kwargs.pop("response_format", None)
            response = await self.client.responses.create(**response_kwargs)
        except OpenAIError as e:
            # Log the full error for debugging
            _LOGGER.error("[v%s] OpenAI API error with full details: %s", INTEGRATION_VERSION, str(e))
            _LOGGER.debug("[v%s] Request that failed: %s", INTEGRATION_VERSION, json.dumps(response_kwargs))
            
            # Check if it's a tools error
            if "tools[0].name" in str(e) or "tools" in str(e):
                _LOGGER.warning("[v%s] Tools error detected, retrying without tools: %s", INTEGRATION_VERSION, e)
                response_kwargs.pop("tools", None)
                response_kwargs.pop("tool_choice", None)
                try:
                    response = await self.client.responses.create(**response_kwargs)
                except Exception as retry_err:
                    _LOGGER.error("[v%s] Retry without tools also failed: %s", INTEGRATION_VERSION, retry_err)
                    raise retry_err
            else:
                raise e
        except Exception as err:
            _LOGGER.error("[v%s] Response API error: %s", INTEGRATION_VERSION, err)
            raise ConfigEntryNotReady(
                "Response API not available or incompatible OpenAI library version."
            ) from err

        _LOGGER.info("[v%s] Response API Prompt for %s: %s", INTEGRATION_VERSION, model, json.dumps(messages))

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

        # Check if the response contains tool calls (proper Responses API format)
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            _LOGGER.info("[v%s] Processing %d tool calls from Responses API", INTEGRATION_VERSION, len(tool_calls))
            for tool_call in tool_calls:
                try:
                    if hasattr(tool_call, 'function'):
                        func_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        _LOGGER.debug("[v%s] Executing tool call: %s with args: %s", INTEGRATION_VERSION, func_name, arguments)
                        
                        # Find the matching function from configured tools
                        functions = self.get_functions()
                        matching_func = next((f for f in functions if f["spec"]["name"] == func_name), None)
                        
                        if matching_func:
                            from .helpers import get_function_executor
                            executor = get_function_executor(matching_func["function"]["type"])
                            result = await executor.execute(
                                self.hass,
                                matching_func["function"],
                                arguments,
                                user_input,
                                exposed_entities,
                            )
                            # Add function result to messages and get natural language response
                            messages.append({
                                "role": "function",
                                "name": func_name,
                                "content": str(result)
                            })
                            messages.append({
                                "role": "system",
                                "content": "The function was executed successfully. Provide a natural language confirmation."
                            })
                            return await self.query(user_input, messages, exposed_entities, n_requests + 1)
                        else:
                            _LOGGER.warning("[v%s] No matching function found for: %s", INTEGRATION_VERSION, func_name)
                            text = f"Unknown function: {func_name}"
                            message.content = text
                except Exception as e:
                    _LOGGER.error("[v%s] Failed to execute tool call: %s", INTEGRATION_VERSION, e)
                    text = f"Error executing tool: {e}"
                    message.content = text
        
        # Fallback: If the model returned JSON in output_text, try to parse and execute
        elif text and (text.strip().startswith('[') or text.strip().startswith('{')):
            try:
                # Extract JSON from text that might have additional text after it
                json_text = text.strip()
                # Try to find just the JSON part if there's text after
                if '{' in json_text or '[' in json_text:
                    # Find the first complete JSON object or array
                    start_idx = 0
                    if json_text[0] == '{':
                        bracket_count = 0
                        for i, char in enumerate(json_text):
                            if char == '{':
                                bracket_count += 1
                            elif char == '}':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    json_text = json_text[:i+1]
                                    break
                    elif json_text[0] == '[':
                        bracket_count = 0
                        for i, char in enumerate(json_text):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    json_text = json_text[:i+1]
                                    break
                
                payload = json.loads(json_text)
                _LOGGER.info("[v%s] Detected JSON in output_text, attempting to parse as tool call", INTEGRATION_VERSION)
                _LOGGER.debug("[v%s] Extracted JSON: %s", INTEGRATION_VERSION, json_text)
                
                # Handle array format: [{"domain":"light","service":"turn_on",...}]
                if isinstance(payload, list):
                    _LOGGER.debug("[v%s] Processing array format with %d items", INTEGRATION_VERSION, len(payload))
                    for item in payload:
                        if isinstance(item, dict) and "domain" in item and "service" in item:
                            # This is a direct service call format
                            from .helpers import get_function_executor
                            executor = get_function_executor("native")
                            fn_config = {"type": "native", "name": "execute_service"}
                            
                            # Normalize the service call format
                            service_call = {
                                "list": [{
                                    "domain": item.get("domain"),
                                    "service": item.get("service"),
                                    "target": item.get("target", {}),
                                    "service_data": item.get("data") or item.get("service_data", {})
                                }]
                            }
                            
                            try:
                                result = await executor.execute(
                                    self.hass,
                                    fn_config,
                                    service_call,
                                    user_input,
                                    exposed_entities,
                                )
                                _LOGGER.info("[v%s] Successfully executed service: %s.%s", INTEGRATION_VERSION, item['domain'], item['service'])
                                # Add confirmation message
                                messages.append({
                                    "role": "system",
                                    "content": f"Successfully executed {item['domain']}.{item['service']}. Provide a natural language confirmation."
                                })
                                return await self.query(user_input, messages, exposed_entities, n_requests + 1)
                            except Exception as e:
                                _LOGGER.error("[v%s] Failed to execute service: %s", INTEGRATION_VERSION, e)
                                text = f"Error: {e}"
                                message.content = text
                
                # Handle object format for backward compatibility
                elif isinstance(payload, dict):
                    parsed_json = None
                    
                    # Check if payload contains a function name as key
                    # Format: {"function_name": <arguments>} where arguments can be list or object
                    functions = self.get_functions()
                    function_names = [f["spec"]["name"] for f in functions]
                    
                    # Try to match any configured function
                    matched_function_name = None
                    for func_name in function_names:
                        if func_name in payload:
                            matched_function_name = func_name
                            break
                    
                    if matched_function_name:
                        _LOGGER.info("[v%s] Detected function call in JSON: %s", INTEGRATION_VERSION, matched_function_name)
                        matching_func = next((f for f in functions if f["spec"]["name"] == matched_function_name), None)
                        
                        if matching_func:
                            from .helpers import get_function_executor
                            executor = get_function_executor(matching_func["function"]["type"])
                            
                            # Get the function arguments
                            func_args_raw = payload[matched_function_name]
                            
                            # Special handling for execute_services which expects {"list": [...]}
                            if matched_function_name == "execute_services" and isinstance(func_args_raw, list):
                                # Convert list to proper parameter format
                                normalized_args = {"list": func_args_raw}
                                _LOGGER.debug("[v%s] Normalized execute_services args: list with %d items", INTEGRATION_VERSION, len(func_args_raw))
                            else:
                                # For other functions, use arguments as-is
                                normalized_args = func_args_raw if isinstance(func_args_raw, dict) else {}
                            
                            try:
                                _LOGGER.info("[v%s] Executing %s with args: %s", INTEGRATION_VERSION, matched_function_name, json.dumps(normalized_args))
                                result = await executor.execute(
                                    self.hass,
                                    matching_func["function"],
                                    normalized_args,
                                    user_input,
                                    exposed_entities,
                                )
                                _LOGGER.info("[v%s] Successfully executed %s from JSON", INTEGRATION_VERSION, matched_function_name)
                                # Return success message
                                text = "Klart!"
                                message.content = text
                            except Exception as e:
                                _LOGGER.error("[v%s] Failed to execute %s from JSON: %s", INTEGRATION_VERSION, matched_function_name, e, exc_info=True)
                                text = f"Fel vid körning av {matched_function_name}: {e}"
                                message.content = text
                        else:
                            _LOGGER.warning("[v%s] Function %s not found in configuration", INTEGRATION_VERSION, matched_function_name)
                            text = f"Funktionen {matched_function_name} finns inte konfigurerad"
                            message.content = text
                    
                    # Check for both "actions" and "calls" keys (different formats from OpenAI)
                    actions_list = payload.get("actions") or payload.get("calls", [])
                    if payload.get("type") == "execute_services" and isinstance(actions_list, list):
                        _LOGGER.info("[v%s] Processing execute_services format with %d actions", INTEGRATION_VERSION, len(actions_list))
                        # Old format compatibility
                        norm = {"execute_services": {"list": []}}
                        for c in actions_list:
                            item = {
                                "domain": c.get("domain"),
                                "service": c.get("service"),
                            }
                            tgt = c.get("target") or {}
                            if "entity_id" in tgt:
                                item["target"] = {"entity_id": tgt["entity_id"]}
                            elif "area_name" in tgt:
                                item["target"] = {"area_name": tgt["area_name"]}
                            elif "area_id" in tgt:
                                # Handle both single area_id and list of area_ids
                                area_ids = tgt["area_id"]
                                if isinstance(area_ids, list):
                                    item["target"] = {"area_name": area_ids[0] if area_ids else ""}
                                else:
                                    item["target"] = {"area_name": area_ids}
                            elif "area" in tgt:
                                item["target"] = {"area_name": tgt["area"]}
                            elif "device_id" in tgt:
                                item["target"] = {"device_id": tgt["device_id"]}
                            data = c.get("service_data") or c.get("data") or {}
                            if data:
                                item["service_data"] = data
                            norm["execute_services"]["list"].append(item)
                        parsed_json = norm
                    else:
                        parsed_json = payload
                    # Check if it looks like a function call request (not a result)
                    # Try to match against any of our known functions
                    functions = self.get_functions()
                    function_names = [f["spec"]["name"] for f in functions]
                    matched_function = None
                    matched_function_name = None
                    
                    # Check if the JSON contains any of our function names as keys
                    for func_name in function_names:
                        if func_name in parsed_json:
                            matched_function_name = func_name
                            matched_function = next(
                                (f for f in functions if f["spec"]["name"] == func_name),
                                None
                            )
                            break
                    
                    if matched_function:
                        _LOGGER.warning(
                            "[v%s] Detected %s function call in response, executing it",
                            INTEGRATION_VERSION,
                            matched_function_name
                        )
                        
                        if n_requests < self.entry.options.get(
                            CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
                            DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
                        ):
                            # Execute the function
                            from .helpers import get_function_executor
                            function_executor = get_function_executor(matched_function["function"]["type"])
                            try:
                                # Extract the arguments for the function
                                # The JSON should have the function name as a key with the arguments as value
                                function_args = parsed_json.get(matched_function_name, parsed_json)
                                
                                result = await function_executor.execute(
                                    self.hass, 
                                    matched_function["function"], 
                                    function_args,  # The function arguments
                                    user_input, 
                                    exposed_entities
                                )
                                _LOGGER.info(
                                    "[v%s] Executed %s function from JSON response: %s",
                                    INTEGRATION_VERSION,
                                    matched_function_name,
                                    result
                                )
                                # Add function result to messages
                                messages.append({
                                    "role": "function",
                                    "name": matched_function_name,
                                    "content": str(result)
                                })
                                # Request a natural language response about what was done
                                messages.append({
                                    "role": "system",
                                    "content": "The function was executed successfully. Provide a natural language confirmation."
                                })
                                # Get natural language response
                                return await self.query(user_input, messages, exposed_entities, n_requests + 1)
                            except Exception as e:
                                _LOGGER.error(
                                    "[v%s] Failed to execute function from JSON: %s",
                                    INTEGRATION_VERSION,
                                    e
                                )
                                text = f"I encountered an error executing that action: {str(e)}"
                                message.content = text
                        else:
                            # Can't execute, provide generic response
                            text = "I understand what you want me to do, but I'm unable to execute that action right now."
                            message.content = text
                    elif isinstance(parsed_json, dict) and any(
                        key in parsed_json for key in ["result", "status", "error"]
                    ):
                        # This looks like a function result, not a call - just convert to text
                        _LOGGER.debug("[v%s] JSON appears to be a result, not a function call", INTEGRATION_VERSION)
                        text = "Action completed."
                        message.content = text
            except json.JSONDecodeError as e:
                _LOGGER.debug("[v%s] Failed to parse JSON from output_text: %s", INTEGRATION_VERSION, e)
                # Keep original output if not JSON
                pass
            except Exception as e:
                _LOGGER.error("[v%s] Error processing JSON tool call: %s", INTEGRATION_VERSION, e)
                # Keep original output on error
                pass

        # Store last response id for this conversation without mutating ConversationInput
        try:
            conversation_id_for_store = getattr(user_input, "conversation_id", None)
        except Exception:
            conversation_id_for_store = None
        if conversation_id_for_store and hasattr(response, "id"):
            self._last_response_ids[conversation_id_for_store] = response.id

        # Token-based history truncation removed

        return OpenAIQueryResponse(response=response, message=message)

    async def execute_function_call(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message,
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
        message,
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
        message,
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
        self, response, message
    ) -> None:
        self.response = response
        self.message = message