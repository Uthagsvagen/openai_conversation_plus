import base64
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.typing import ConfigType
from openai import AsyncOpenAI
from openai._exceptions import OpenAIError

from .const import DOMAIN, SERVICE_QUERY_IMAGE, GPT5_MODELS, INTEGRATION_VERSION

QUERY_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry"): selector.ConfigEntrySelector(
            {
                "integration": DOMAIN,
            }
        ),
        vol.Required("model", default="gpt-5"): cv.string,  # Ändra till GPT-5
        vol.Required("prompt"): cv.string,
        vol.Required("images"): vol.All(cv.ensure_list, [{"url": cv.string}]),
        vol.Optional("max_tokens", default=300): cv.positive_int,
        vol.Optional("reasoning_level", default="medium"): cv.string,  # Lägg till GPT-5 parametrar
        vol.Optional("verbosity", default="medium"): cv.string,
    }
)

_LOGGER = logging.getLogger(__package__)


async def async_setup_services(hass: HomeAssistant, config: ConfigType) -> None:
    """Set up services for the openai conversation plus component."""

    async def query_image(call: ServiceCall) -> ServiceResponse:
        """Query an image using Responses API with GPT-5 support."""
        try:
            model = call.data["model"]
            reasoning_level = call.data.get("reasoning_level", "medium")
            verbosity = call.data.get("verbosity", "medium")
            
            # Skapa messages för Responses API
            messages = [
                {
                    "role": "user", 
                    "content": call.data["prompt"]
                }
            ]
            
            # Lägg till bilder som attachments (GPT-5 stöd)
            if call.data.get("images"):
                # För GPT-5, hantera bilder som attachments
                attachments = []
                for image in call.data["images"]:
                    attachments.append({
                        "type": "image_url",
                        "image_url": to_image_param(hass, image)
                    })
                messages[0]["attachments"] = attachments

            _LOGGER.info("[v%s] Prompt for %s: %s", INTEGRATION_VERSION, model, messages)

            # Använd Responses API istället för Chat Completions
            response_kwargs = {
                "model": model,
                "input": messages,  # Responses API använder 'input'
                "max_output_tokens": call.data["max_tokens"],  # Responses API använder 'max_output_tokens'
            }
            
            # Lägg till GPT-5 specifika parametrar
            if model in GPT5_MODELS:
                response_kwargs["reasoning"] = {"effort": reasoning_level}
                if verbosity:
                    # Map legacy verbosity values
                    from .const import VERBOSITY_COMPAT_MAP
                    mapped_verbosity = VERBOSITY_COMPAT_MAP.get(verbosity, verbosity)
                    response_kwargs["text"] = {"verbosity": mapped_verbosity}

            _LOGGER.debug("[v%s] Full response_kwargs being sent to API: %s", INTEGRATION_VERSION, response_kwargs)

            response = await AsyncOpenAI(
                api_key=hass.data[DOMAIN][call.data["config_entry"]]["api_key"]
            ).responses.create(**response_kwargs)
            
            # Extrahera text från Responses API
            text = getattr(response, "output_text", None)
            if not text and hasattr(response, "output") and response.output:
                try:
                    first = response.output[0]
                    parts = getattr(first, "content", []) or []
                    texts = []
                    for p in parts:
                        t = getattr(getattr(p, "text", None), "value", None)
                        if t:
                            texts.append(t)
                    text = "\n".join(texts) if texts else None
                except Exception:
                    pass
            
            response_dict = {
                "content": text or "",
                "model": model,
                "usage": getattr(response, "usage", None)
            }
            
            _LOGGER.info("[v%s] Response %s", INTEGRATION_VERSION, response_dict)
            
        except OpenAIError as err:
            raise HomeAssistantError(f"Error generating image response: {err}") from err

        return response_dict

    hass.services.async_register(
        DOMAIN,
        SERVICE_QUERY_IMAGE,
        query_image,
        schema=QUERY_IMAGE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def to_image_param(hass: HomeAssistant, image) -> dict:
    """Convert url to base64 encoded image if local."""
    url = image["url"]

    if urlparse(url).scheme in cv.EXTERNAL_URL_PROTOCOL_SCHEMA_LIST:
        return {"url": url}

    if not hass.config.is_allowed_path(url):
        raise HomeAssistantError(
            f"Cannot read `{url}`, no access to path; "
            "`allowlist_external_dirs` may need to be adjusted in "
            "`configuration.yaml`"
        )
    if not Path(url).exists():
        raise HomeAssistantError(f"`{url}` does not exist")
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type is None or not mime_type.startswith("image"):
        raise HomeAssistantError(f"`{url}` is not an image")

    return {"url": f"data:{mime_type};base64,{encode_image(url)}"}


def encode_image(image_path):
    """Convert to base64 encoded image."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
