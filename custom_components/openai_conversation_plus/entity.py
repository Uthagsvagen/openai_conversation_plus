"""Base entity for OpenAI Conversation Plus integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.httpx_client import get_async_client

from openai import AsyncOpenAI
from openai._exceptions import OpenAIError

from .const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_ORGANIZATION,
    CONF_REASONING_LEVEL,
    CONF_STORE_CONVERSATIONS,
    CONF_VERBOSITY,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REASONING_LEVEL,
    DEFAULT_STORE_CONVERSATIONS,
    DEFAULT_VERBOSITY,
    DOMAIN,
    INTEGRATION_VERSION,
    VERBOSITY_COMPAT_MAP,
    is_gpt5_model,
)

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
            "model": self._config_entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL),
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
        # Prefer the configured AsyncOpenAI client from runtime_data (set in __init__.py),
        # but fall back to constructing one if needed.
        client = getattr(self._config_entry, "runtime_data", None)
        if not isinstance(client, AsyncOpenAI):
            api_key = self._config_entry.data.get(CONF_API_KEY)
            if not api_key:
                raise ValueError("OpenAI API key not found in config entry")
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._config_entry.data.get(CONF_BASE_URL),
                organization=self._config_entry.data.get(CONF_ORGANIZATION),
                http_client=get_async_client(self.hass),
            )

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

        try:
            options = self._config_entry.options or {}
            model = options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
            max_tokens = options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            response_kwargs: dict[str, Any] = {
                "model": model,
                "input": messages,
                "max_output_tokens": max_tokens,
                "store": options.get(CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS),
            }

            # Apply GPT‑5 reasoning/verbosity controls when using GPT‑5 family models
            if is_gpt5_model(model):
                reasoning_level = options.get(CONF_REASONING_LEVEL, DEFAULT_REASONING_LEVEL)
                verbosity = options.get(CONF_VERBOSITY, DEFAULT_VERBOSITY)
                mapped_verbosity = VERBOSITY_COMPAT_MAP.get(verbosity, verbosity)
                response_kwargs["reasoning"] = {"effort": reasoning_level}
                response_kwargs["text"] = {
                    "verbosity": mapped_verbosity,
                    "format": {"type": "text"},
                }

            _LOGGER.debug(
                "[v%s] AI Task responses.create kwargs (model=%s, max_output_tokens=%s, structured=%s)",
                INTEGRATION_VERSION,
                model,
                max_tokens,
                bool(structure),
            )

            response = await client.responses.create(**response_kwargs)

            # Extract text from Responses API response
            content = getattr(response, "output_text", None) or ""
            if not content and hasattr(response, "output") and response.output:
                try:
                    for output_item in response.output:
                        if getattr(output_item, "type", "") == "message":
                            content_items = getattr(output_item, "content", []) or []
                            for content_item in content_items:
                                if getattr(content_item, "type", "") == "output_text":
                                    text = getattr(content_item, "text", "")
                                    if text:
                                        content += text + "\n"
                    content = content.strip()
                except Exception:
                    content = content.strip() if content else ""

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

        except OpenAIError as e:
            _LOGGER.error("[v%s] OpenAI API error handling AI Task: %s", INTEGRATION_VERSION, e)
            return {"error": str(e)}
        except Exception as e:
            _LOGGER.error("[v%s] Error handling AI Task chat log: %s", INTEGRATION_VERSION, e)
            return {"error": str(e)}
