# OpenAI Conversation Plus

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

<div align="center">
  <img src="custom_components/openai_conversation_plus/logo/logo.png" alt="OpenAI Conversation Plus Logo" width="128" height="128">
</div>

OpenAI Conversation Plus is a custom Home Assistant integration that enhances the native conversation experience with modern OpenAI capabilities: GPT‑5 model support, streaming responses, built‑in web search, and powerful custom tool calls (functions).

This project is a fork of Extended OpenAI Conversation. Big thanks to the original creator, [jekalmin](https://github.com/jekalmin), for the excellent foundation and inspiration.

- Original project: `extended_openai_conversation`
- Examples in the original project: https://github.com/jekalmin/extended_openai_conversation/tree/main/examples

## Key Features

- **GPT‑5 family support** (where available) - Uses OpenAI Responses API exclusively
- **Streaming responses** for real-time conversational experience
- **MCP (Model Context Protocol) servers** - Connect to external tools and services
- Native web search integration (Response API powered)
- Custom tool calls (functions) with Home Assistant service execution
- AI Task support for structured data generation
- **Responses API only** - Optimized for the latest OpenAI capabilities (no fallback to Chat Completions)

## Requirements

- Home Assistant 2025.8.1 or newer
- Python 3.11+
- OpenAI API key 
- **OpenAI Python Library 1.101.0 or newer** (required)

## Installation

[![Open your Home Assistant instance and show the add integration dialog for a specific integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=openai_conversation_plus)

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Add this repository as a custom repository: `Uthagsvagen/openai_conversation_plus`
3. Install the integration
4. Restart Home Assistant

### Manual Installation
1. Copy the folder `custom_components/openai_conversation_plus/` into your Home Assistant `config/custom_components/` directory
2. Ensure you have OpenAI Python library 1.101.0+ installed (Home Assistant will install this automatically)
3. Restart Home Assistant

## Preparations

1. Obtain an OpenAI API key
2. (Optional) If you use a custom/compatible endpoint, provide your base URL and organization
3. Decide whether to enable Response API features like web search and conversation storage

## How It Works

OpenAI Conversation Plus registers as a Home Assistant Conversation agent and follows the official Conversation API flow. It:

- Builds a system prompt with your custom instructions
- **Automatically includes all exposed entities** in the system context (sent only once per conversation to save tokens)
- Sends messages to OpenAI using the Responses API exclusively
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
- MCP servers configuration (connect to external tools and services)

### System Prompt & Entity Context

**Important:** You no longer need to include `exposed_entities` in your prompt template. The integration automatically:

- **Includes all exposed entities** in the system context behind the scenes
- **Sends entities only once per conversation** (saves context tokens on subsequent messages)
- **Bypasses Home Assistant's template size limits** by appending entities directly in code
- **Uses exposure filter** with fallback to all entities if none are specifically exposed

Your prompt template should focus on instructions and personality - entity information is handled automatically.

## MCP (Model Context Protocol) Servers

OpenAI Conversation Plus supports connecting to MCP servers, allowing your assistant to interact with external tools and services. MCP is OpenAI's protocol for tool connectivity.

Configure MCP servers in the integration options using YAML format:

### Simple List Format:
```yaml
- server_label: "Home Assistant"
  server_url: "https://ha.domain.com/mcp_server/sse"
  server_api_key: "your-api-key"
- server_label: "Google Sheets"
  server_url: "https://sheets.example.com/sse"
  server_api_key: "another-key"
```

### Compatible with mcpServers Format:
```yaml
mcpServers:
  Home Assistant:
    command: mcp-proxy
    args:
      - https://ha.domain.com/mcp_server/sse
    env:
      API_ACCESS_TOKEN: your-api-key
  Sheets:
    url: https://sheets.example.com/sse
    api_key: another-key
```

MCP servers allow your assistant to:
- Access external databases and APIs
- Control remote systems
- Integrate with third-party services
- Extend functionality beyond Home Assistant

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

**Important:** This integration uses OpenAI's Responses API exclusively (no Chat Completions fallback). This means:
- **Streaming**: Real-time token streaming for responsive conversations (Responses API native)
- **GPT‑5 Models**: Full support for GPT‑5 family models with enhanced reasoning and verbosity controls
- **Web Search**: Native web search capability for fetching fresh information with citations

Configure in the integration options:
- Enable streaming for real-time responses (enabled by default)
- Web search context size (low/medium/high)
- Optional user location for geo-aware search results

## AI Tasks (Structured Data)

The integration supports AI Tasks for generating structured outputs (e.g., JSON). Provide an optional JSON schema to guide the output and parse the result into Home Assistant.

## Examples & Videos

The original project by `jekalmin` includes several examples and reference materials:
- Examples directory: https://github.com/jekalmin/extended_openai_conversation/tree/main/examples
- You'll also find helpful videos under: https://github.com/jekalmin/ explaining different usage scenarios

## Future Plans

We're actively working on expanding the capabilities of OpenAI Conversation Plus with the following planned features:

### 🔍 **RAG (Retrieval-Augmented Generation)**
- **Local RAG Database**: Implement local vector database for document storage and retrieval
- **Knowledge Base Integration**: Allow users to upload and query custom documents
- **Semantic Search**: Advanced search capabilities across stored knowledge
- **Context-Aware Responses**: Generate responses based on relevant stored information

### 🤖 **Multi-Agent Configuration**
- **Agent Orchestration**: Coordinate multiple specialized AI agents
- **Role-Based Agents**: Different agents for different tasks (security, energy, entertainment)
- **Agent Communication**: Enable agents to collaborate and share information
- **Workflow Automation**: Complex multi-step automation workflows

### 🌐 **Multi-LLM Provider Support**
- **OpenAI Alternatives**: Support for Claude, Gemini, and other LLM providers
- **Local Models**: Integration with local models like Ollama and LM Studio
- **Provider Switching**: Easy switching between different LLM providers or use several for different tasks. This can already be achieved by creating functions to call oter conversation agents. 


### 🚀 **Advanced Features**
- **Custom Embeddings**: Support for custom embedding models
- **Performance Monitoring**: Track and optimize response times and costs

*These features are planed for development. Follow our releases for updates!*

## Credits

- Forked from: `extended_openai_conversation` by [jekalmin](https://github.com/jekalmin)
- Community contributions and Home Assistant developers

## Support & Issues

- Open issues and feature requests here: `https://github.com/Uthagsvagen/openai_conversation_plus/issues`
- Enable debug logs if you need to report a bug:
```yaml
logger:
  logs:
    custom_components.openai_conversation_plus: debug
    homeassistant.components.conversation: debug
```

## License

This project follows the same open-source spirit as the original. See repository for license details.
