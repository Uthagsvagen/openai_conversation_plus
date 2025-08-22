"""Global fixtures for Extended OpenAI Conversation integration tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME

from custom_components.extended_openai_conversation.const import (
    DOMAIN,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom integrations."""
    yield


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Return a mock config entry."""
    return ConfigEntry(
        domain=DOMAIN,
        title="Extended OpenAI Conversation",
        data={
            CONF_NAME: "Test Assistant",
            CONF_API_KEY: "test-api-key",
        },
        options={
            "chat_model": DEFAULT_CHAT_MODEL,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "top_p": DEFAULT_TOP_P,
        },
        entry_id="test_entry_id",
        version=1,
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("custom_components.extended_openai_conversation.AsyncOpenAI") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Mock chat completions
        chat_mock = MagicMock()
        completions_mock = MagicMock()
        create_mock = AsyncMock()
        
        # Set up the chain of mocks
        client_instance.chat = chat_mock
        chat_mock.completions = completions_mock
        completions_mock.create = create_mock
        
        # Mock response
        response_mock = MagicMock()
        response_mock.choices = [
            MagicMock(
                message=MagicMock(
                    content="Test response",
                    role="assistant",
                    function_call=None,
                    tool_calls=None
                ),
                finish_reason="stop"
            )
        ]
        response_mock.usage = MagicMock(
            total_tokens=100,
            completion_tokens=50,
            prompt_tokens=50
        )
        
        create_mock.return_value = response_mock
        
        # Mock responses API
        responses_mock = MagicMock()
        client_instance.responses = responses_mock
        responses_mock.create = AsyncMock(return_value=response_mock)
        
        yield client_instance


@pytest.fixture
def mock_validate_authentication():
    """Mock authentication validation."""
    with patch(
        "custom_components.extended_openai_conversation.helpers.validate_authentication",
        return_value=None
    ) as mock:
        yield mock


@pytest.fixture
async def integration_setup(hass: HomeAssistant, mock_config_entry: ConfigEntry, mock_openai_client, mock_validate_authentication):
    """Set up the integration."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
