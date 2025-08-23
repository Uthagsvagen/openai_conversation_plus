"""Test AI Task functionality."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openai_conversation_plus.ai_task import (
    AI_TASK_AVAILABLE,
    OpenAITaskEntity,
    async_setup_entry,
)
from custom_components.openai_conversation_plus.const import DOMAIN


@pytest.mark.skipif(not AI_TASK_AVAILABLE, reason="AI Task component not available")
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    integration_setup,
):
    """Test setting up AI Task platform."""
    async_add_entities = AsyncMock()

    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    # Check that one entity was added
    assert async_add_entities.called
    assert len(async_add_entities.call_args[0][0]) == 1
    entity = async_add_entities.call_args[0][0][0]
    assert isinstance(entity, OpenAITaskEntity)


@pytest.mark.skipif(not AI_TASK_AVAILABLE, reason="AI Task component not available")
async def test_ai_task_entity(
    hass: HomeAssistant,
    mock_config_entry,
    mock_openai_client,
):
    """Test AI Task entity."""
    entity = OpenAITaskEntity(hass, mock_config_entry)

    assert entity._attr_unique_id == f"{mock_config_entry.entry_id}_ai_task"
    assert entity._attr_name == "AI Task"

    # Test device info
    device_info = entity.device_info
    assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
    assert device_info["name"] == mock_config_entry.title
    assert device_info["manufacturer"] == "OpenAI"


@pytest.mark.skipif(not AI_TASK_AVAILABLE, reason="AI Task component not available")
async def test_generate_data_simple_text(
    hass: HomeAssistant,
    mock_config_entry,
    integration_setup,
):
    """Test generating data with simple text prompt."""
    entity = OpenAITaskEntity(hass, mock_config_entry)

    # Mock the AI Task classes if available
    if AI_TASK_AVAILABLE:
        from homeassistant.components import ai_task, conversation

        # Create mock task
        task = MagicMock()
        task.prompt = "Generate a summary"
        task.name = "test_task"
        task.structure = None

        # Create mock chat log
        chat_log = MagicMock()
        chat_log.content = [MagicMock(content="Generate a summary", role="user")]
        chat_log.conversation_id = "test_conversation"

        # Mock the handler
        with patch.object(
            entity,
            "_async_handle_chat_log",
            return_value={"response": "This is a summary"},
        ):
            result = await entity._async_generate_data(task, chat_log)

        assert hasattr(result, "data")
        assert result.data == "This is a summary"
        assert result.conversation_id == "test_conversation"


@pytest.mark.skipif(not AI_TASK_AVAILABLE, reason="AI Task component not available")
async def test_generate_data_with_structure(
    hass: HomeAssistant,
    mock_config_entry,
    integration_setup,
):
    """Test generating structured data."""
    entity = OpenAITaskEntity(hass, mock_config_entry)

    if AI_TASK_AVAILABLE:
        from homeassistant.components import ai_task, conversation

        # Create mock task with structure
        task = MagicMock()
        task.prompt = "Generate user data"
        task.name = "structured_task"
        task.structure = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        }

        # Create mock chat log
        chat_log = MagicMock()
        chat_log.content = [MagicMock(content="Generate user data", role="user")]
        chat_log.conversation_id = "test_conversation"

        # Mock the handler to return structured data
        structured_response = {"name": "John Doe", "age": 30}
        with patch.object(
            entity, "_async_handle_chat_log", return_value={"data": structured_response}
        ):
            result = await entity._async_generate_data(task, chat_log)

        assert hasattr(result, "data")
        assert result.data == structured_response
        assert result.conversation_id == "test_conversation"
