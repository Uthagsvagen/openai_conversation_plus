"""Test OpenAI Conversation Plus integration setup."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.conversation import DOMAIN as CONVERSATION_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.openai_conversation_plus import (
    OpenAIAgent,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.openai_conversation_plus.const import DATA_AGENT, DOMAIN


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_openai_client,
    mock_validate_authentication,
):
    """Test setup of config entry."""
    mock_config_entry.add_to_hass(hass)

    # Mock conversation.async_set_agent
    with patch(
        "custom_components.openai_conversation_plus.conversation.async_set_agent"
    ) as mock_set_agent:
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
        side_effect=Exception("Authentication failed"),
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
    with patch(
        "custom_components.openai_conversation_plus.conversation.async_unset_agent"
    ) as mock_unset_agent:
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


def test_normalize_mcp_items():
    """Test MCP configuration normalization."""
    from custom_components.openai_conversation_plus import _normalize_mcp_items

    # Test simple list format
    data = [
        {"server_label": "Test", "server_url": "https://test.com", "server_api_key": "key1"},
        {"label": "Test2", "url": "https://test2.com", "api_key": "key2"},
    ]
    result = _normalize_mcp_items(data)
    assert len(result) == 2
    assert result[0]["server_label"] == "Test"
    assert result[0]["server_url"] == "https://test.com"
    assert result[0]["server_api_key"] == "key1"
    assert result[1]["server_label"] == "Test2"
    assert result[1]["server_url"] == "https://test2.com"
    assert result[1]["server_api_key"] == "key2"

    # Test mcpServers format
    data = {
        "mcpServers": {
            "Test": {
                "url": "https://test.com",
                "api_key": "key1",
            },
            "Test2": {
                "args": ["https://test2.com"],
                "env": {"API_ACCESS_TOKEN": "key2"},
            },
        }
    }
    result = _normalize_mcp_items(data)
    assert len(result) == 2
    assert result[0]["server_label"] == "Test"
    assert result[0]["server_url"] == "https://test.com"
    assert result[0]["server_api_key"] == "key1"
    assert result[1]["server_label"] == "Test2"
    assert result[1]["server_url"] == "https://test2.com"
    assert result[1]["server_api_key"] == "key2"


def test_build_mcp_tools_from_options():
    """Test building MCP tools from options."""
    from custom_components.openai_conversation_plus import build_mcp_tools_from_options
    from custom_components.openai_conversation_plus.const import CONF_MCP_SERVERS

    # Test with valid YAML
    options = {
        CONF_MCP_SERVERS: """
- server_label: "Test"
  server_url: "https://test.com"
  server_api_key: "key1"
- server_label: "Test2"
  server_url: "https://test2.com"
"""
    }
    tools = build_mcp_tools_from_options(options)
    assert len(tools) == 2
    assert tools[0]["type"] == "mcp"
    assert tools[0]["server_label"] == "Test"
    assert tools[0]["server_url"] == "https://test.com"
    assert tools[0]["server_api_key"] == "key1"
    assert tools[1]["type"] == "mcp"
    assert tools[1]["server_label"] == "Test2"
    assert tools[1]["server_url"] == "https://test2.com"
    assert "server_api_key" not in tools[1]

    # Test with empty/invalid YAML
    options = {CONF_MCP_SERVERS: ""}
    tools = build_mcp_tools_from_options(options)
    assert tools == []

    options = {CONF_MCP_SERVERS: "invalid yaml {"}
    tools = build_mcp_tools_from_options(options)
    assert tools == []
