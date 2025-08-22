# Extended OpenAI Conversation

Extended OpenAI Conversation integration for Home Assistant that enhances the default OpenAI conversation agent with additional features and customization options.

## Current Status

This integration is under active development. Recent updates include:

✅ **Completed Features:**
- Response API migration with backward compatibility
- GPT-5 model support (gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-pro)
- Native web search integration
- AI Task platform for structured data generation
- Streaming support for Chat Completions API
- Enhanced safety features
- Comprehensive testing framework

🚧 **In Progress:**
- Documentation updates
- Frontend UI components
- Additional Response API features

## Features

### Core Features
- **OpenAI Response API**: Next-generation API with enhanced capabilities
- **Multiple Model Support**: GPT-4, GPT-4o, GPT-5 variants, and custom models
- **Web Search**: Built-in internet search capabilities
- **AI Tasks**: Generate structured data from natural language
- **Custom Functions**: Define custom functions accessible from Home Assistant UI
- **Streaming Responses**: Real-time response streaming for better UX
- **Context Management**: Intelligent conversation history management

### Configuration Options
- Response API toggle
- Web search enable/disable
- Search context size (low/medium/high)
- User location for geo-aware searches
- Reasoning level for GPT-5 models
- Verbosity control
- Conversation persistence
- Custom prompt templates
- Function call limits
- Temperature and token controls

## Installation

### HACS (Recommended)
1. Add this repository to HACS: `jekalmin/extended_openai_conversation`
2. Install from HACS store
3. Restart Home Assistant

### Manual
1. Copy `custom_components/extended_openai_conversation` to your config directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Extended OpenAI Conversation"
4. Enter your OpenAI API key and configure options

### Basic Configuration
- **Name**: Assistant name
- **API Key**: Your OpenAI API key
- **Model**: Select AI model (GPT-4, GPT-5, etc.)

### Advanced Options
- **Use Response API**: Enable new Response API features
- **Enable Web Search**: Allow AI to search the internet
- **Reasoning Level**: Thinking intensity (minimal/low/medium/high)
- **Custom Functions**: YAML configuration for custom functions

## Usage

### Voice Commands
Simply use Home Assistant's voice assistant or type in the conversation interface:
- "Turn on the living room lights"
- "What's the weather like?"
- "Search the web for the latest news about AI"
- "Generate a shopping list based on my calendar events"

### AI Tasks
Create automations that use AI for structured data:
```yaml
service: conversation.process
data:
  agent_id: YOUR_AGENT_ID
  text: "Extract all email addresses from this text..."
```

### Custom Functions
Define custom functions in the configuration:
```yaml
functions:
  - spec:
      name: get_weather
      description: Get weather for a location
      parameters:
        type: object
        properties:
          location:
            type: string
    function:
      type: rest
      url: https://api.weather.com/...
```

## Development

### Testing
Run tests without Home Assistant:
```bash
python run_tests.py
```

Or use make:
```bash
make test
```

See [README_TESTING.md](README_TESTING.md) for detailed testing documentation.

### Contributing
1. Fork the repository
2. Create a feature branch
3. Run tests: `make validate-all`
4. Submit a pull request

## Requirements
- Home Assistant 2024.1 or newer
- Python 3.11+
- OpenAI API key

## License
MIT License - see LICENSE file for details

## Support
- [GitHub Issues](https://github.com/jekalmin/extended_openai_conversation/issues)
- [Home Assistant Community](https://community.home-assistant.io/)

## Acknowledgments
Based on the official Home Assistant OpenAI Conversation integration with extended functionality.
