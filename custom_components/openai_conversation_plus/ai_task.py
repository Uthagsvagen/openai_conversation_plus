"""AI Task integration for OpenAI Conversation Plus."""

from __future__ import annotations

import logging
from json import JSONDecodeError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads

# Try to import AI Task components
try:
    from homeassistant.components import ai_task, conversation

    AI_TASK_AVAILABLE = True
except ImportError:
    AI_TASK_AVAILABLE = False
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.warning("AI Task component not available")

from .entity import OpenAIBaseLLMEntity
from .const import INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AI Task entities."""
    if not AI_TASK_AVAILABLE:
        _LOGGER.info("[v%s] AI Task component not available, skipping AI Task entity setup", INTEGRATION_VERSION)
        return

    # Create a single AI Task entity for this config entry
    async_add_entities([OpenAITaskEntity(hass, config_entry)])


if AI_TASK_AVAILABLE:

    class OpenAITaskEntity(
        ai_task.AITaskEntity,
        OpenAIBaseLLMEntity,
    ):
        """OpenAI AI Task entity."""

        _attr_supported_features = (
            ai_task.AITaskEntityFeature.GENERATE_DATA
            | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS
        )

        def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
            """Initialize the AI Task entity."""
            super().__init__(hass, config_entry, "AI Task")
            self._attr_unique_id = f"{config_entry.entry_id}_ai_task"

        async def _async_generate_data(
            self,
            task: ai_task.GenDataTask,
            chat_log: conversation.ChatLog,
        ) -> ai_task.GenDataTaskResult:
            """Handle a generate data task."""
            # Convert ChatLog to list of messages for our handler
            messages = []

            for content in chat_log.content:
                if isinstance(content, conversation.UserContent):
                    role = "user"
                    text = content.content
                elif isinstance(content, conversation.AssistantContent):
                    role = "assistant"
                    text = content.content
                elif hasattr(content, "role") and hasattr(content, "content"):
                    role = content.role
                    text = content.content
                else:
                    continue

                if text:
                    messages.append({"role": role, "content": text})

            # Call our base handler
            result = await self._async_handle_chat_log(
                messages,
                task.name if hasattr(task, "name") else "data_generation",
                task.structure if hasattr(task, "structure") else None,
            )

            # Extract the response
            if "error" in result:
                raise HomeAssistantError(f"Error generating data: {result['error']}")

            if "data" in result:
                data = result["data"]
            elif "response" in result:
                # Try to parse as JSON if structure was requested
                if hasattr(task, "structure") and task.structure:
                    try:
                        data = json_loads(result["response"])
                    except JSONDecodeError:
                        data = result["response"]
                else:
                    data = result["response"]
            else:
                data = result

            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=data,
            )

else:
    # Fallback implementation if AI Task is not available
    class OpenAITaskEntity(OpenAIBaseLLMEntity):
        """Fallback OpenAI Task entity when AI Task component is not available."""

        def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
            """Initialize the fallback entity."""
            super().__init__(hass, config_entry, "AI Task")
            self._attr_unique_id = f"{config_entry.entry_id}_ai_task"
            _LOGGER.info("[v%s] Created fallback AI Task entity", INTEGRATION_VERSION)
