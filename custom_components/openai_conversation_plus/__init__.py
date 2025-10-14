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
    """Set up OpenAI Conversation from a config entry."""
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

    # Validate authentication
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

    # Create OpenAI client for conversation platform to use
    client = AsyncOpenAI(
        api_key=entry.data[CONF_API_KEY],
        base_url=entry.data.get(CONF_BASE_URL),
        organization=entry.data.get(CONF_ORGANIZATION),
        http_client=get_async_client(hass),
    )
    
    # Store client in runtime_data for conversation.py to access
    entry.runtime_data = client  # type: ignore[attr-defined]
    
    # Store entry data for backward compatibility
    data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    data[CONF_API_KEY] = entry.data[CONF_API_KEY]

    # Forward to platforms (conversation.py will register the agent)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("[v%s] OpenAI Conversation Plus setup complete", INTEGRATION_VERSION)
    
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
    _LOGGER.info("[v%s] Building MCP tools from configuration...", INTEGRATION_VERSION)
    
    if not raw or not raw.strip():
        _LOGGER.info("[v%s] No MCP servers configured", INTEGRATION_VERSION)
        return []
    
    try:
        data = yaml.safe_load(raw)
        _LOGGER.debug("[v%s] Parsed MCP YAML data: %s", INTEGRATION_VERSION, data)
    except yaml.YAMLError as e:
        _LOGGER.error(
            "[v%s] Failed to parse MCP YAML configuration: %s\n"
            "YAML content preview:\n%s\n"
            "Tips: Remove quotes around API keys, check indentation, ensure no line breaks in values",
            INTEGRATION_VERSION, 
            e,
            raw[:500] if len(raw) > 500 else raw
        )
        return []
    except Exception as e:
        _LOGGER.error("[v%s] Unexpected error parsing MCP configuration: %s", INTEGRATION_VERSION, e)
        return []
    
    items = _normalize_mcp_items(data) if data else []
    _LOGGER.info("[v%s] Normalized %d MCP server configurations", INTEGRATION_VERSION, len(items))
    
    tools = []
    for idx, it in enumerate(items):
        server_label = it.get("server_label")
        server_url = it.get("server_url")
        
        if server_label and server_url:
            tool = {
                "type": "mcp",
                "server_label": server_label,
                "server_url": server_url,
                "require_approval": it.get("require_approval", "never"),
            }
            
            # Add API key if present (don't log the full key for security)
            if it.get("server_api_key"):
                tool["server_api_key"] = it["server_api_key"]
                api_key_preview = it["server_api_key"][:10] + "..." if len(it["server_api_key"]) > 10 else "***"
                _LOGGER.info(
                    "[v%s] MCP Server #%d: '%s' at %s (API key: %s)",
                    INTEGRATION_VERSION,
                    idx + 1,
                    server_label,
                    server_url,
                    api_key_preview
                )
            else:
                _LOGGER.info(
                    "[v%s] MCP Server #%d: '%s' at %s (no API key)",
                    INTEGRATION_VERSION,
                    idx + 1,
                    server_label,
                    server_url
                )
            
            # Add allowed_tools if specified
            if it.get("allowed_tools"):
                # Support both list and comma-separated string
                allowed = it["allowed_tools"]
                if isinstance(allowed, str):
                    tool["allowed_tools"] = [t.strip() for t in allowed.split(",")]
                elif isinstance(allowed, list):
                    tool["allowed_tools"] = allowed
                _LOGGER.info(
                    "[v%s]   - Allowed tools: %s",
                    INTEGRATION_VERSION,
                    ", ".join(tool["allowed_tools"])
                )
            else:
                _LOGGER.info("[v%s]   - All tools allowed (no restriction)", INTEGRATION_VERSION)
            
            _LOGGER.debug(
                "[v%s]   - Require approval: %s",
                INTEGRATION_VERSION,
                tool["require_approval"]
            )
            
            tools.append(tool)
        else:
            _LOGGER.warning(
                "[v%s] Skipping MCP server #%d: missing server_label or server_url (label=%s, url=%s)",
                INTEGRATION_VERSION,
                idx + 1,
                server_label,
                server_url
            )
    
    _LOGGER.info("[v%s] Successfully built %d MCP tools", INTEGRATION_VERSION, len(tools))
    return tools


def sanitize_tools_for_responses(tools: list[dict]) -> list[dict]:
    """Sanitize tools for the Responses API by removing unsupported fields.

    - Removes secret-bearing or non-spec fields from tools where not supported
    - Ensures function tools use the flat structure {type:function, name:..., description:..., parameters:...}
    - Keeps only known fields for web_search and mcp tool types
    """
    sanitized: list[dict] = []
    for original in tools or []:
        try:
            tool_type = original.get("type")
            if tool_type == "function":
                # Responses API requires flat structure
                if "function" in original and isinstance(original["function"], dict):
                    # Convert nested format to flat format
                    sanitized.append({
                        "type": "function",
                        "name": original["function"].get("name"),
                        "description": original["function"].get("description", ""),
                        "parameters": original["function"].get("parameters", {"type": "object", "properties": {}}),
                    })
                elif original.get("name"):
                    # Already flat format
                    sanitized.append({
                        "type": "function",
                        "name": original.get("name"),
                        "description": original.get("description", ""),
                        "parameters": original.get("parameters", {"type": "object", "properties": {}}),
                    })
            elif tool_type == "web_search":
                ws: dict[str, Any] = {"type": "web_search"}
                if "search_context_size" in original:
                    ws["search_context_size"] = original["search_context_size"]
                if "user_location" in original and isinstance(original["user_location"], dict):
                    loc = original["user_location"]
                    ws["user_location"] = {
                        "type": loc.get("type", "approximate"),
                        "country": loc.get("country", ""),
                        "city": loc.get("city", ""),
                        "region": loc.get("region", ""),
                    }
                sanitized.append(ws)
            elif tool_type == "mcp":
                # Keep known MCP fields including credentials and allowed tool list
                mcp: dict[str, Any] = {"type": "mcp"}
                if original.get("server_label"):
                    mcp["server_label"] = original["server_label"]
                if original.get("server_url"):
                    mcp["server_url"] = original["server_url"]
                # Preserve require_approval as provided (defaulting handled elsewhere)
                if original.get("require_approval"):
                    mcp["require_approval"] = original["require_approval"]
                # Preserve server_api_key for MCP authentication
                if original.get("server_api_key"):
                    mcp["server_api_key"] = original["server_api_key"]
                # Preserve allowed_tools if provided (list or comma-separated string)
                if original.get("allowed_tools") is not None:
                    mcp["allowed_tools"] = original["allowed_tools"]
                sanitized.append(mcp)
            else:
                _LOGGER.debug("[v%s] Dropping unknown tool type during sanitize: %s", INTEGRATION_VERSION, tool_type)
        except Exception as e:
            _LOGGER.debug("[v%s] Failed to sanitize tool %s: %s", INTEGRATION_VERSION, original, e)
            continue
    return sanitized

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


# OpenAIAgent class removed - Home Assistant now uses OpenAIConversationEntity from conversation.py
# All agent functionality is in conversation.py to eliminate code duplication
