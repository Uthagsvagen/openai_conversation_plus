"""Base entity for OpenAI Conversation Plus integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)


class OpenAIBaseLLMEntity(Entity):
    """Base class for OpenAI LLM entities."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry, name: str) -> None:
        """Initialize the OpenAI entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = (
            f"{config_entry.entry_id}_{name.lower().replace(' ', '_')}"
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": self._config_entry.title,
            "manufacturer": "OpenAI",
            "model": self._config_entry.options.get("chat_model", "gpt-4o-mini"),
            "entry_type": "service",
        }

    async def _async_handle_chat_log(
        self, chat_log: list[dict], task_name: str, structure: dict | None = None
    ) -> dict[str, Any]:
        """Handle conversation log and generate response.

        Args:
            chat_log: List of conversation messages
            task_name: Name of the task being performed
            structure: Optional JSON schema for structured output

        Returns:
            Dictionary containing the response data
        """
        # Get the conversation agent
        from . import OpenAIAgent

        agent_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        agent: OpenAIAgent = agent_data.get("agent")

        if not agent:
            raise ValueError("OpenAI agent not found")

        # Build messages from chat log
        messages = []
        for entry in chat_log:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role and content:
                messages.append({"role": role, "content": content})

        # If structure is provided, add it to the system message
        if structure and messages:
            # Find or create system message
            system_msg_idx = None
            for idx, msg in enumerate(messages):
                if msg.get("role") == "system":
                    system_msg_idx = idx
                    break

            structure_prompt = f"\n\nYou must respond with valid JSON that conforms to the following schema:\n{structure}"

            if system_msg_idx is not None:
                messages[system_msg_idx]["content"] += structure_prompt
            else:
                # Insert system message at the beginning
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": f"You are an AI assistant helping with the task: {task_name}.{structure_prompt}",
                    },
                )

        # Create a mock ConversationInput object
        class MockConversationInput:
            def __init__(self):
                self.text = ""
                self.language = "en"
                self.conversation_id = None
                self.device_id = None
                self.context = type("Context", (), {"user_id": None})()
                self.agent_response_id = None

        mock_input = MockConversationInput()

        # Get exposed entities for context
        exposed_entities = agent.get_exposed_entities()

        try:
            # Query the agent
            response = await agent.query(
                mock_input,
                messages,
                exposed_entities,
                0,  # No function calls for structured data generation
            )

            content = response.message.content

            # If structure was provided, try to parse JSON
            if structure:
                import json

                try:
                    # Extract JSON from the response
                    # The response might contain markdown code blocks
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        if end > start:
                            content = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        if end > start:
                            content = content[start:end].strip()

                    data = json.loads(content)
                    return {"data": data}
                except json.JSONDecodeError as e:
                    _LOGGER.error("[v%s] Failed to parse JSON response: %s", INTEGRATION_VERSION, e)
                    return {
                        "error": f"Failed to parse JSON (v{INTEGRATION_VERSION}): {str(e)}",
                        "raw_response": content,
                    }
            else:
                return {"response": content}

        except Exception as e:
            _LOGGER.error("[v%s] Error handling chat log: %s", INTEGRATION_VERSION, e)
            return {"error": str(e)}
