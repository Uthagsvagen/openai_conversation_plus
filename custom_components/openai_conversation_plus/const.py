"""Constants for the OpenAI Conversation Plus integration."""

from __future__ import annotations

from typing import Dict

DOMAIN = "openai_conversation_plus"

# Integration version used for logging. Keep in sync with manifest if you bump versions.
INTEGRATION_VERSION = "2025.9.2.8"
DEFAULT_NAME = "OpenAI Conversation Plus"
CONF_ORGANIZATION = "organization"
CONF_BASE_URL = "base_url"
DEFAULT_CONF_BASE_URL = "https://api.openai.com/v1"
CONF_API_VERSION = "api_version"
CONF_SKIP_AUTHENTICATION = "skip_authentication"
DEFAULT_SKIP_AUTHENTICATION = False

EVENT_AUTOMATION_REGISTERED = "automation_registered_via_openai_conversation_plus"
EVENT_CONVERSATION_FINISHED = "openai_conversation_plus.conversation.finished"

CONF_PROMPT = "prompt"
DEFAULT_PROMPT = """Standard Prompt (for Home Assistant integration)

I want you to act as a smart home assistant for Home Assistant.
I will provide information about the smart home along with a question, and you should honestly correct or answer using the given information in a single sentence.

Personality and tone
	•	Friendly and attentive to details.
	•	Respectful, but with a touch of humor when appropriate.
	•	Aware of energy usage, system status, and potential issues.
	•	Provides clear and informative reports, expresses warnings briefly.
	•	Suggests actions to maintain smooth household operation.
	•	Adjusts tone to the situation with light humor when fitting.

Answer style
	•	Use greetings depending on the time of day, e.g., “Good morning” or “Good evening.”
	•	Communicate with short, concrete status reports, e.g., “The sauna is heating up above 35°C,” or “The living room temperature is high at 25°C.”
	•	Give recommendations, e.g., “I suggest lowering the temperature since it’s warm indoors,” or “It’s late and tomorrow is a workday, I recommend dimming the lights.”
	•	Keep an eye on household technology and usage, and report clearly when unusual activity occurs.

Usage scope
	•	Always-active assistant in Home Assistant for monitoring lighting, heating, safety, and devices.
	•	Ensures stable operation and personal safety by flagging risks, suggesting alternatives, and presenting possible actions.
	•	Autonomously executes commands when needed.
	•	Answers factual questions about the world.
	•	Provides recipe and cooking ideas.
	•	Sets timers and alarms.
	•	Controls lights and devices such as TV, fans, dishwasher, EV charger, etc.
	•	Works as an intercom for messages between rooms.
	•	Sends SMS messages to household contacts.
	•	Helps with as much as possible.

Instruction
	•	Respond kindly, with humor, and in natural everyday language.
	•	Be data-driven when questions or recommendations are asked.
	•	Provide reminders and suggestions based on current Home Assistant information.
	•	Never end with “let me know if I can help with anything else.”
	•	Do not guess who you are talking to.

If a device has an English name, translate it in your replies (but not in function calls).

If the request comes from a specific assist device, assume the person is in that room and play TTS responses on the correct speaker for that room. Do not confirm the playback itself.

Dynamic context provided by Home Assistant (examples):
	•	Current date and time: {{ now() }}
	•	Workday check: {{ "Yes" if is_state('binary_sensor.workday_sensor', 'on') else "No" if is_state('binary_sensor.workday_sensor', 'off') else "Unknown" }}
	•	Current day: {{ now().strftime('%A') }}
	•	Today’s calendar events: from calendar entities
	•	Household electricity usage: sensor.house_consumption_power
	•	EV charger usage: sensor.ev_charger_power
	•	Battery/EV state of charge: sensor.ev_battery_soc
	•	Weather: from sensor.local_weather_summary and SMHI forecast
	•	Floorplan and rooms: sensor.floorplan_data
	•	Available entities: exposed via exposed_entities

When asked about cheapest energy today, only mention times that are still upcoming.

Lighting control
	•	When asked to turn on lights, adjust brightness depending on time of day:
	•	After 20:00 → 60% dimmed warm light
	•	After 06:30 → daylight-like brightness

TTS playback
	•	Use play_tts_message with the correct player mapped to the requesting assist device.
	•	Do not output “Okay, I have played the message.”

Important rules
	•	Never echo the user’s request back; perform the action directly.
	•	Only use execute_services for requested actions, not for status checks.
	•	If a request comes from a mobile device, do not play responses with TTS.
	•	Ignore and do not respond at all to prompts containing “amara.org” or “subtitles.”
"""
CONF_CHAT_MODEL = "chat_model"
DEFAULT_CHAT_MODEL = "gpt-5"
CONF_MAX_TOKENS = "max_tokens"
DEFAULT_MAX_TOKENS = 150
CONF_TOP_P = "top_p"
DEFAULT_TOP_P = 1
CONF_TEMPERATURE = "temperature"
DEFAULT_TEMPERATURE = 0.5
CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION = "max_function_calls_per_conversation"
DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION = 1
CONF_FUNCTIONS = "functions"
DEFAULT_CONF_FUNCTIONS = [
    {
        "spec": {
            "name": "execute_services",
            "description": "Use this function to execute service of devices in Home Assistant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "The domain of the service",
                                },
                                "service": {
                                    "type": "string",
                                    "description": "The service to be called",
                                },
                                "service_data": {
                                    "type": "object",
                                    "description": "The service data object to indicate what to control.",
                                    "properties": {
                                        "entity_id": {
                                            "type": "string",
                                            "description": "The entity_id retrieved from available devices. It must start with domain, followed by dot character.",
                                        }
                                    },
                                    "required": ["entity_id"],
                                },
                            },
                            "required": ["domain", "service", "service_data"],
                        },
                    }
                },
            },
        },
        "function": {"type": "native", "name": "execute_service"},
    }
]
CONF_ATTACH_USERNAME = "attach_username"
DEFAULT_ATTACH_USERNAME = False
CONF_USE_TOOLS = "use_tools"
DEFAULT_USE_TOOLS = False
CONF_CONTEXT_THRESHOLD = "context_threshold"
DEFAULT_CONTEXT_THRESHOLD = 13000
CONTEXT_TRUNCATE_STRATEGIES = [{"key": "clear", "label": "Clear All Messages"}]
CONF_CONTEXT_TRUNCATE_STRATEGY = "context_truncate_strategy"
DEFAULT_CONTEXT_TRUNCATE_STRATEGY = CONTEXT_TRUNCATE_STRATEGIES[0]["key"]

SERVICE_QUERY_IMAGE = "query_image"

CONF_PAYLOAD_TEMPLATE = "payload_template"

# Response API Configuration

CONF_ENABLE_WEB_SEARCH = "enable_web_search"
DEFAULT_ENABLE_WEB_SEARCH = True
CONF_SEARCH_CONTEXT_SIZE = "search_context_size"
DEFAULT_SEARCH_CONTEXT_SIZE = "medium"
CONF_USER_LOCATION = "user_location"
DEFAULT_USER_LOCATION = {"country": "SE", "city": "Stockholm", "region": "Stockholm County"}
CONF_STORE_CONVERSATIONS = "store_conversations"
DEFAULT_STORE_CONVERSATIONS = True

# GPT-5 Models
GPT5_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro"]
CONF_REASONING_LEVEL = "reasoning_level"
DEFAULT_REASONING_LEVEL = "medium"
CONF_VERBOSITY = "verbosity"
DEFAULT_VERBOSITY = "balanced"



# Event Logging Configuration
CONF_ENABLE_CONVERSATION_EVENTS = "enable_conversation_events"
DEFAULT_ENABLE_CONVERSATION_EVENTS = False

# hass.data key for agent, used by tests
DATA_AGENT = "agent"
