"""Config flow for OpenAI Conversation integration."""
from __future__ import annotations

import logging
import types
from types import MappingProxyType
from typing import Any
import json
from json import JSONDecodeError

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    ObjectSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from openai._exceptions import APIConnectionError, AuthenticationError

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
    CONTEXT_TRUNCATE_STRATEGIES,
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
    GPT5_MODELS,
    INTEGRATION_VERSION,
)
from . import helpers

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = None  # Built dynamically to support selectors

DEFAULT_CONF_FUNCTIONS_STR = yaml.dump(DEFAULT_CONF_FUNCTIONS, sort_keys=False)

DEFAULT_OPTIONS = types.MappingProxyType(
    {
        CONF_PROMPT: DEFAULT_PROMPT,
        CONF_CHAT_MODEL: DEFAULT_CHAT_MODEL,
        CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
        CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION: DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
        CONF_TOP_P: DEFAULT_TOP_P,
        CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
        CONF_FUNCTIONS: DEFAULT_CONF_FUNCTIONS_STR,
        CONF_ATTACH_USERNAME: DEFAULT_ATTACH_USERNAME,
        CONF_USE_TOOLS: DEFAULT_USE_TOOLS,
        CONF_CONTEXT_THRESHOLD: DEFAULT_CONTEXT_THRESHOLD,
        CONF_CONTEXT_TRUNCATE_STRATEGY: DEFAULT_CONTEXT_TRUNCATE_STRATEGY,
        CONF_ENABLE_WEB_SEARCH: DEFAULT_ENABLE_WEB_SEARCH,
        CONF_SEARCH_CONTEXT_SIZE: DEFAULT_SEARCH_CONTEXT_SIZE,
        CONF_STORE_CONVERSATIONS: DEFAULT_STORE_CONVERSATIONS,
        CONF_REASONING_LEVEL: DEFAULT_REASONING_LEVEL,
        CONF_VERBOSITY: DEFAULT_VERBOSITY,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api_key = data[CONF_API_KEY]
    base_url = data.get(CONF_BASE_URL)
    api_version = data.get(CONF_API_VERSION)
    organization = data.get(CONF_ORGANIZATION)
    skip_authentication = data.get(CONF_SKIP_AUTHENTICATION)

    await helpers.validate_authentication(
        hass=hass,
        api_key=api_key,
        base_url=base_url,
        api_version=api_version,
        organization=organization,
        skip_authentication=skip_authentication,
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenAI Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            # Build schema with selectors so we can show multiline user_location
            default_location_str = json.dumps(DEFAULT_USER_LOCATION, indent=2)
            schema = {
                vol.Optional(CONF_NAME): str,
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_CONF_BASE_URL): str,
                vol.Optional(CONF_API_VERSION): str,
                vol.Optional(CONF_ORGANIZATION): str,
                vol.Optional(
                    CONF_SKIP_AUTHENTICATION, default=DEFAULT_SKIP_AUTHENTICATION
                ): BooleanSelector(),
                vol.Optional(
                    CONF_USER_LOCATION,
                    description={"suggested_value": default_location_str},
                    default=default_location_str,
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)),
            }
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(schema), errors={}
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except (APIConnectionError, ConnectionError):
            errors["base"] = "cannot_connect"
        except AuthenticationError:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("[v%s] Authentication failed or unexpected exception", INTEGRATION_VERSION)
            errors["base"] = "invalid_auth"
        else:
            entry_data = dict(user_input)
            # Remove skip_authentication if it's the default value, tests expect minimal keys
            if entry_data.get(CONF_SKIP_AUTHENTICATION, DEFAULT_SKIP_AUTHENTICATION) == DEFAULT_SKIP_AUTHENTICATION:
                entry_data.pop(CONF_SKIP_AUTHENTICATION, None)
            # Do not store user_location in data (options are used for runtime settings)
            entry_data.pop(CONF_USER_LOCATION, None)
            return self.async_create_entry(
                title=entry_data.get(CONF_NAME, DEFAULT_NAME), data=entry_data
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """OpenAI config flow options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        try:
            if user_input is not None:
                # Parse user_location JSON if provided as text
                if isinstance(user_input.get(CONF_USER_LOCATION), str):
                    try:
                        user_input[CONF_USER_LOCATION] = json.loads(user_input[CONF_USER_LOCATION])
                    except JSONDecodeError:
                        # If invalid JSON, drop it so default applies
                        user_input.pop(CONF_USER_LOCATION, None)
                return self.async_create_entry(title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input)
            schema = self.openai_config_option_schema(self.config_entry.options)
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(schema),
            )
        except Exception as err:
            _LOGGER.error("[v%s] Error in options flow: %s", INTEGRATION_VERSION, err)
            return self.async_abort(reason="unknown")

    def openai_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        """Return a schema for OpenAI completion options."""
        if not options:
            options = DEFAULT_OPTIONS

        schema: dict = {}

        # One-line textboxes and simple inputs first
        schema[vol.Optional(
            CONF_CHAT_MODEL,
            description={
                # New key in HA 2023.4
                "suggested_value": options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
            },
            default=DEFAULT_CHAT_MODEL,
        )] = str
        schema[vol.Optional(
            CONF_MAX_TOKENS,
            description={"suggested_value": options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)},
            default=DEFAULT_MAX_TOKENS,
        )] = int
        schema[vol.Optional(
            CONF_TOP_P,
            description={"suggested_value": options.get(CONF_TOP_P, DEFAULT_TOP_P)},
            default=DEFAULT_TOP_P,
        )] = NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05))
        schema[vol.Optional(
            CONF_TEMPERATURE,
            description={"suggested_value": options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)},
            default=DEFAULT_TEMPERATURE,
        )] = NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.1))

        # Checkboxes
        schema[vol.Optional(
            CONF_ATTACH_USERNAME,
            description={"suggested_value": options.get(CONF_ATTACH_USERNAME, DEFAULT_ATTACH_USERNAME)},
            default=DEFAULT_ATTACH_USERNAME,
        )] = BooleanSelector()
        schema[vol.Optional(
            CONF_USE_TOOLS,
            description={"suggested_value": options.get(CONF_USE_TOOLS, DEFAULT_USE_TOOLS)},
            default=DEFAULT_USE_TOOLS,
        )] = BooleanSelector()
        schema[vol.Optional(
            CONF_ENABLE_WEB_SEARCH,
            description={"suggested_value": options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH)},
            default=DEFAULT_ENABLE_WEB_SEARCH,
        )] = BooleanSelector()
        schema[vol.Optional(
            CONF_STORE_CONVERSATIONS,
            description={"suggested_value": options.get(CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS)},
            default=DEFAULT_STORE_CONVERSATIONS,
        )] = BooleanSelector()
        schema[vol.Optional(
            CONF_ENABLE_CONVERSATION_EVENTS,
            description={"suggested_value": options.get(CONF_ENABLE_CONVERSATION_EVENTS, DEFAULT_ENABLE_CONVERSATION_EVENTS)},
            default=DEFAULT_ENABLE_CONVERSATION_EVENTS,
        )] = BooleanSelector()

        # Select lists
        schema[vol.Optional(
            CONF_CONTEXT_TRUNCATE_STRATEGY,
            description={
                "suggested_value": options.get(
                    CONF_CONTEXT_TRUNCATE_STRATEGY,
                    DEFAULT_CONTEXT_TRUNCATE_STRATEGY,
                )
            },
            default=DEFAULT_CONTEXT_TRUNCATE_STRATEGY,
        )] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=strategy["key"], label=strategy["label"])
                    for strategy in CONTEXT_TRUNCATE_STRATEGIES
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        schema[vol.Optional(
            CONF_SEARCH_CONTEXT_SIZE,
            description={"suggested_value": options.get(CONF_SEARCH_CONTEXT_SIZE, DEFAULT_SEARCH_CONTEXT_SIZE)},
            default=DEFAULT_SEARCH_CONTEXT_SIZE,
        )] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value="low", label="Low"),
                    SelectOptionDict(value="medium", label="Medium"),
                    SelectOptionDict(value="high", label="High"),
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        schema[vol.Optional(
            CONF_REASONING_LEVEL,
            description={"suggested_value": options.get(CONF_REASONING_LEVEL, DEFAULT_REASONING_LEVEL)},
            default=DEFAULT_REASONING_LEVEL,
        )] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value="minimal", label="Minimal"),
                    SelectOptionDict(value="low", label="Low"),
                    SelectOptionDict(value="medium", label="Medium"),
                    SelectOptionDict(value="high", label="High"),
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        # Map legacy values to Responses API supported values
        verbosity_default = options.get(CONF_VERBOSITY, DEFAULT_VERBOSITY)
        from .const import VERBOSITY_COMPAT_MAP
        verbosity_default = VERBOSITY_COMPAT_MAP.get(verbosity_default, verbosity_default)
        schema[vol.Optional(
            CONF_VERBOSITY,
            description={"suggested_value": verbosity_default},
            default=verbosity_default,
        )] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value="low", label="Low"),
                    SelectOptionDict(value="medium", label="Medium"),
                    SelectOptionDict(value="high", label="High"),
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

        # Other single-line inputs
        schema[vol.Optional(
            CONF_CONTEXT_THRESHOLD,
            description={
                "suggested_value": options.get(CONF_CONTEXT_THRESHOLD, DEFAULT_CONTEXT_THRESHOLD)
            },
            default=DEFAULT_CONTEXT_THRESHOLD,
        )] = int
        schema[vol.Optional(
            CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
            description={
                "suggested_value": options.get(
                    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
                    DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
                )
            },
            default=DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
        )] = int
        default_location_str = json.dumps(
            options.get(CONF_USER_LOCATION, DEFAULT_USER_LOCATION), indent=2
        )
        schema[vol.Optional(
            CONF_USER_LOCATION,
            description={"suggested_value": default_location_str},
            default=default_location_str,
        )] = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True))

        # Multiline text areas last
        schema[vol.Optional(
            CONF_FUNCTIONS,
            description={"suggested_value": options.get(CONF_FUNCTIONS, DEFAULT_CONF_FUNCTIONS_STR)},
            default=DEFAULT_CONF_FUNCTIONS_STR,
        )] = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True))
        schema[vol.Optional(
            CONF_PROMPT,
            description={"suggested_value": options.get(CONF_PROMPT, DEFAULT_PROMPT)},
            default=DEFAULT_PROMPT,
        )] = TemplateSelector()

        return schema
