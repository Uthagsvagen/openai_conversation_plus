"""Test the OpenAI Conversation Plus config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.openai_conversation_plus.const import (
    CONF_BASE_URL,
    DEFAULT_CONF_BASE_URL,
    DEFAULT_NAME,
    DOMAIN,
)


async def test_form(hass: HomeAssistant, mock_validate_authentication) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.openai_conversation_plus.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Test Assistant",
                CONF_API_KEY: "test-api-key",
                CONF_BASE_URL: DEFAULT_CONF_BASE_URL,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Assistant"
    assert result2["data"] == {
        CONF_NAME: "Test Assistant",
        CONF_API_KEY: "test-api-key",
        CONF_BASE_URL: DEFAULT_CONF_BASE_URL,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.openai_conversation_plus.helpers.validate_authentication",
        side_effect=Exception("Invalid API key"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Test Assistant",
                CONF_API_KEY: "invalid-key",
                CONF_BASE_URL: DEFAULT_CONF_BASE_URL,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.openai_conversation_plus.helpers.validate_authentication",
        side_effect=ConnectionError(),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Test Assistant",
                CONF_API_KEY: "test-api-key",
                CONF_BASE_URL: DEFAULT_CONF_BASE_URL,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry, mock_validate_authentication
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "chat_model": "gpt-4",
            "max_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.9,
        },
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        "chat_model": "gpt-4",
        "max_tokens": 200,
        "temperature": 0.7,
        "top_p": 0.9,
    }
