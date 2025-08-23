# OpenAI Conversation Plus

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

<div align="center">
  <img src="logos/openai_conversation_plus.svg" alt="OpenAI Conversation Plus Logo" width="128" height="128">
</div>

OpenAI Conversation Plus is a custom Home Assistant integration that enhances the native conversation experience with modern OpenAI capabilities: GPT‑5 model support, streaming responses, built‑in web search, and powerful custom tool calls (functions).

This project is a fork of Extended OpenAI Conversation. Big thanks to the original creator, [jekalmin](https://github.com/jekalmin), for the excellent foundation and inspiration.

- Original project: `extended_openai_conversation`
- Examples in the original project: https://github.com/jekalmin/extended_openai_conversation/tree/main/examples

## Key Features

- GPT‑5 family support (where available)
- Streaming responses for a responsive UX
- Native web search integration (Response API powered)
- Custom tool calls (functions) with Home Assistant service execution
- AI Task support for structured data generation
- Backward compatible with classic Chat Completions where needed

## Requirements

- Home Assistant 2024.1.0 or newer
- Python 3.11+
- OpenAI API key (or compatible endpoint)

## Installation

[![Open your Home Assistant instance and show the add integration dialog for a specific integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=openai_conversation_plus)

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Add this repository as a custom repository: `aselling/openai_conversation_plus`
3. Install the integration
4. Restart Home Assistant

### Manual Installation
1. Copy the folder `custom_components/openai_conversation_plus/` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Preparations

1. Obtain an OpenAI API key
2. (Optional) If you use a custom/compatible endpoint, provide your base URL and organization
3. Decide whether to enable Response API features like web search and conversation storage

## How It Works

OpenAI Conversation Plus registers as a Home Assistant Conversation agent and follows the official Conversation API flow. It:

- Builds a system prompt with knowledge of your exposed entities
- Sends messages to OpenAI (Response API or Chat Completions)
- Streams or returns the final response
- Executes custom tools (functions) to call Home Assistant services when appropriate

For more about the Conversation API, see Home Assistant documentation:
`https://developers.home-assistant.io/docs/intent_conversation_api/`

## Configuration

Go to Settings → Devices & Services → Add Integration → OpenAI Conversation Plus.

Typical options:
- Model (e.g., GPT‑4o, GPT‑5 variants if available)
- Temperature, top_p, and max tokens
- Use Response API (enable advanced features)
- Enable Web Search (and configure search depth and user location)
- Conversation storage (persist conversation state server‑side)
- Reasoning level and verbosity (for GPT‑5 variants)
- Custom functions (YAML) and max function calls per conversation

## Functions (Custom Tool Calls)

Define custom functions to extend the agent with your automation logic. You can map function specs to:
- Native Home Assistant service execution
- REST calls
- Other supported executors

Example spec (simplified):
```yaml
functions:
  - spec:
      name: execute_services
      description: Execute Home Assistant services
      parameters:
        type: object
        properties:
          list:
            type: array
            items:
              type: object
              properties:
                domain: { type: string }
                service: { type: string }
                service_data:
                  type: object
                  properties:
                    entity_id: { type: string }
                  required: [entity_id]
              required: [domain, service, service_data]
    function:
      type: native
      name: execute_service
```

### Function Usage
- The agent decides when to call a function (`auto`) or you can limit calls per conversation
- Use confirmations for safety where appropriate
- Great for device control, querying states, or orchestrating complex automations

## Streaming & Web Search

- Streaming (Chat Completions): enables incremental tokens for faster perceived responses
- Web Search (Response API): allows the model to fetch fresh information and include citations

Configure both in the integration options. Web search supports:
- Search context size (low/medium/high)
- Optional user location for better local results

## AI Tasks (Structured Data)

The integration supports AI Tasks for generating structured outputs (e.g., JSON). Provide an optional JSON schema to guide the output and parse the result into Home Assistant.

## Examples & Videos

The original project by `jekalmin` includes several examples and reference materials:
- Examples directory: https://github.com/jekalmin/extended_openai_conversation/tree/main/examples
- You’ll also find helpful videos under: https://github.com/jekalmin/ explaining different usage scenarios

## Credits

- Forked from: `extended_openai_conversation` by [jekalmin](https://github.com/jekalmin)
- Community contributions and Home Assistant developers

## Support & Issues

- Open issues and feature requests here: `https://github.com/aselling/openai_conversation_plus/issues`
- Enable debug logs if you need to report a bug:
```yaml
logger:
  logs:
    custom_components.openai_conversation_plus: debug
    homeassistant.components.conversation: debug
```

## License

This project follows the same open-source spirit as the original. See repository for license details.
