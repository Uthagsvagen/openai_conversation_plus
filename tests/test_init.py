"""Test Extended OpenAI Conversation integration setup."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from homeassistant.components.conversation import DOMAIN as CONVERSATION_DOMAIN

from custom_components.openai_conversation_plus import (
    async_setup_entry,
    async_unload_entry,
    OpenAIAgent,
)
from custom_components.openai_conversation_plus.const import DOMAIN, DATA_AGENT


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_openai_client,
    mock_validate_authentication,
):
    """Test setup of config entry."""
    mock_config_entry.add_to_hass(hass)
    
    # Mock conversation.async_set_agent
    with patch("custom_components.openai_conversation_plus.conversation.async_set_agent") as mock_set_agent:
        result = await async_setup_entry(hass, mock_config_entry)
    
    assert result is True
    assert mock_config_entry.state is ConfigEntryState.LOADED
    
    # Check that the agent was registered
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert DATA_AGENT in hass.data[DOMAIN][mock_config_entry.entry_id]
    
    agent = hass.data[DOMAIN][mock_config_entry.entry_id][DATA_AGENT]
    assert isinstance(agent, OpenAIAgent)
    
    # Check that the agent was set in conversation
    mock_set_agent.assert_called_once_with(hass, mock_config_entry, agent)


async def test_setup_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry,
    mock_openai_client,
):
    """Test setup with authentication failure."""
    mock_config_entry.add_to_hass(hass)
    
    with patch(
        "custom_components.openai_conversation_plus.helpers.validate_authentication",
        side_effect=Exception("Authentication failed")
    ):
        result = await async_setup_entry(hass, mock_config_entry)
    
    assert result is False


async def test_unload_entry(
    hass: HomeAssistant,
    integration_setup,
):
    """Test unloading a config entry."""
    mock_config_entry = integration_setup
    
    # Mock conversation.async_unset_agent
    with patch("custom_components.openai_conversation_plus.conversation.async_unset_agent") as mock_unset_agent:
        result = await async_unload_entry(hass, mock_config_entry)
    
    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    mock_unset_agent.assert_called_once_with(hass, mock_config_entry)


async def test_agent_initialization(
    hass: HomeAssistant,
    mock_config_entry,
    mock_openai_client,
):
    """Test OpenAI agent initialization."""
    agent = OpenAIAgent(hass, mock_config_entry)
    
    assert agent.hass is hass
    assert agent.entry is mock_config_entry
    assert agent.history == {}
    assert agent.client is not None
    assert agent.supported_languages == "*"
