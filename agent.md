# Extended OpenAI Conversation - Home Assistant Integration

## Overview

The **Extended OpenAI Conversation** is a powerful Home Assistant integration that enhances your smart home with advanced AI conversation capabilities. This integration extends the standard conversation component by integrating with OpenAI's language models, providing intelligent responses and automated control of your smart home devices.

**Important Note**: This integration is based on the official [Home Assistant OpenAI Conversation integration](https://www.home-assistant.io/integrations/openai_conversation) and is designed to be fully compatible with Home Assistant's Assist API. The source code for the official integration can be found at [home-assistant/core](https://github.com/home-assistant/core/tree/dev/homeassistant/components/openai_conversation).

## Compatibility & Architecture

### Official Integration Foundation
This integration extends the official Home Assistant OpenAI Conversation component by implementing the same core interfaces and response formats. It inherits from `conversation.AbstractConversationAgent` and follows the exact same conversation flow as the official integration.

### Assist API Compatibility
To work seamlessly with Home Assistant's Assist API, this integration must return responses in the exact format expected by the conversation system:
- **Response Format**: Uses `conversation.ConversationResult` with `intent.IntentResponse`
- **Agent Registration**: Properly registers with `conversation.async_set_agent()`
- **Message Processing**: Follows the same message flow as the official integration
- **Function Calling**: Implements the same function execution pattern

### Response Structure
The integration returns responses that match the official component's structure:
```python
intent_response = intent.IntentResponse(language=user_input.language)
intent_response.async_set_speech(query_response.message.content)
return conversation.ConversationResult(
    response=intent_response, conversation_id=conversation_id
)
```

### Reference Implementations
For developers interested in the exact response format requirements, refer to:
- **Official OpenAI Integration**: [home-assistant/core/openai_conversation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/openai_conversation)
- **Google Generative AI Integration**: [home-assistant/core/google_generative_ai_conversation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/google_generative_ai_conversation)

The Google Generative AI integration is particularly useful as it represents the latest conversation agent implementation and shows the current best practices for Home Assistant conversation agents.

## Upcoming Features & Roadmap

### 🚀 Response API Migration (In Progress)
The integration is being upgraded to use OpenAI's new Responses API, which is a superset of the Chat Completions API. This migration will bring:
- **Built-in Web Search**: Real-time internet search without external integrations
- **Enhanced File Search**: Improved document analysis capabilities
- **State Management**: Optional server-side conversation persistence
- **Multi-tool Orchestration**: Execute multiple tools in a single API call
- **Computer Use**: Future capability for AI-controlled computer interfaces

### 🤖 GPT-5 Model Support (Planned)
Support for the next generation of OpenAI models is being added:
- **GPT-5 & GPT-5-mini**: Advanced models with PhD-level expertise
- **Extended Context**: 272,000 token input window (~200,000 words)
- **Reasoning Levels**: Configurable thinking intensity (minimal/low/medium/high)
- **Personality Modes**: Cynic, Robot, Listener, and Nerd interaction styles

### 🔍 Native Web Search Integration (Coming Soon)
Web search capabilities will be directly integrated into the conversation flow:
- **Automatic Triggering**: AI decides when to search the web
- **Citation Support**: Automatic source attribution
- **Location-Aware**: Geographic context for local searches
- **Configurable Depth**: Control search comprehensiveness

### 📋 AI Task Entities (In Development)
New entity type for structured task execution:
- **Structured Data Generation**: Generate JSON/structured outputs
- **Multi-modal Support**: Handle text, images, and documents
- **Task Automation**: Create reusable AI-powered tasks

For detailed implementation plans and progress, see the [AI Agent Task List](ai_agent_task_list.md).

## Key Features

### 🤖 AI-Powered Smart Home Management
- **Smart Home Manager**: Acts as an intelligent assistant that understands your smart home setup
- **Device Awareness**: Automatically detects and monitors all exposed entities in your Home Assistant instance
- **Contextual Responses**: Provides accurate answers based on real-time device states and information

### 🔧 Advanced Function Calling
- **Service Execution**: Can execute Home Assistant services to control devices
- **Function Management**: Configurable function calls with safety limits
- **Smart Automation**: Automatically registers automations for seamless integration

### 🖼️ Image Analysis Capabilities
- **Vision Model Support**: Query images using GPT-4 Vision models
- **Multi-Image Processing**: Handle multiple images in a single query
- **Customizable Prompts**: Tailor image analysis to your specific needs

### ⚙️ Flexible Configuration
- **Multiple AI Models**: Support for various OpenAI models (GPT-4, GPT-4o-mini, etc.)
- **Custom Prompts**: Fully customizable prompt templates
- **Context Management**: Intelligent context truncation strategies
- **Authentication Options**: Support for both OpenAI and Azure OpenAI endpoints

## Installation

### HACS Installation (Recommended)
1. Install HACS in your Home Assistant instance
2. Add this repository to HACS: `jekalmin/extended_openai_conversation`
3. Install the integration from the HACS store
4. Restart Home Assistant

### Manual Installation
1. Download the integration files
2. Place them in your `custom_components/extended_openai_conversation/` directory
3. Restart Home Assistant

## Configuration

### Initial Setup
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Extended OpenAI Conversation"
4. Enter your configuration details

### Required Configuration
- **Name**: A friendly name for your integration instance
- **API Key**: Your OpenAI API key
- **Base URL**: OpenAI API endpoint (default: `https://api.openai.com/v1`)
- **API Version**: API version to use
- **Organization**: Your OpenAI organization ID (optional)
- **Skip Authentication**: Skip authentication for testing (default: false)

### Advanced Options
- **Prompt Template**: Customize the AI's behavior and knowledge
- **Completion Model**: Choose your preferred OpenAI model
- **Max Tokens**: Control response length
- **Temperature**: Adjust response creativity (0.0 = focused, 1.0 = creative)
- **Top P**: Control response diversity
- **Max Function Calls**: Limit automated service executions per conversation
- **Functions**: Define custom functions for the AI to use
- **Attach Username**: Include user information in conversations
- **Use Tools**: Enable advanced tool usage
- **Context Threshold**: Set token limit for conversation context
- **Context Truncation Strategy**: Choose how to handle long conversations

### New Options (Coming with Response API)
- **Enable Web Search**: Allow AI to search the internet for current information
- **Search Context Size**: Control search depth (low/medium/high)
- **User Location**: Set geographic context for location-aware searches
- **Reasoning Level**: Adjust thinking intensity (minimal/low/medium/high)
- **Verbosity**: Control response length (terse/balanced/expansive)
- **Response Format**: Choose structured output format (text/json_object)
- **Store Conversations**: Enable server-side conversation persistence
- **Safety Level**: Configure content filtering (strict/balanced/relaxed)

## Services

### `query_image`
Analyze images using AI vision models.

**Parameters:**
- `config_entry`: The configuration entry to use
- `model`: Vision model (e.g., `gpt-4-vision-preview`)
- `prompt`: Question about the image
- `images`: List of images to analyze
- `max_tokens`: Maximum response length (default: 300)

**Example:**
```yaml
service: extended_openai_conversation.query_image
data:
  config_entry: !input config_entry
  model: gpt-4-vision-preview
  prompt: "What's in this image?"
  images:
    - url: "https://example.com/image.jpg"
  max_tokens: 300
```

## Usage Examples

### Basic Conversation
The integration automatically integrates with Home Assistant's conversation component. Simply use voice commands or type in the conversation interface:

- "Turn on the living room lights"
- "What's the temperature in the bedroom?"
- "Show me all my smart devices"

### Image Analysis
Use the `query_image` service to analyze security camera feeds, identify objects, or get descriptions of images:

```yaml
automation:
  - alias: "Analyze Motion Detection"
    trigger:
      platform: state
      entity_id: camera.front_door
    action:
      service: extended_openai_conversation.query_image
      data:
        config_entry: !input openai_config
        model: gpt-4-vision-preview
        prompt: "What triggered this motion detection?"
        images:
          - url: "{{ states('camera.front_door') }}"
```

### Custom Functions
The integration supports custom function definitions for specialized use cases:

```yaml
functions:
  - spec:
      name: "custom_device_control"
      description: "Control specific devices with custom logic"
      parameters:
        type: object
        properties:
          device_id:
            type: string
            description: "Device to control"
          action:
            type: string
            description: "Action to perform"
        required: ["device_id", "action"]
    function:
      type: "native"
      name: "execute_custom_service"
```

## Technical Implementation

### Core Architecture
This integration implements the same core architecture as the official Home Assistant conversation agents:

1. **Agent Class**: Extends `conversation.AbstractConversationAgent`
2. **Message Processing**: Implements `async_process()` method for handling user input
3. **Response Generation**: Returns `conversation.ConversationResult` objects
4. **Function Execution**: Supports OpenAI function calling with Home Assistant service execution
5. **Context Management**: Handles conversation history and context truncation

### Key Differences from Official Integration
While maintaining full compatibility, this integration adds several enhancements:

- **Extended Function Support**: Additional function executors for REST, scraping, and database operations
- **Advanced Context Management**: Configurable context thresholds and truncation strategies
- **Custom Function Definitions**: Support for user-defined function specifications
- **Image Analysis Service**: Dedicated service for vision model queries
- **Enhanced Prompt Templates**: More sophisticated system prompts with device information

### Response Flow
```
User Input → Conversation Input → OpenAI API → Function Execution → Response Processing → Conversation Result
```

### Enhanced Features from Research

Based on analysis of the official integrations, the following features are being added:

#### **Streaming Support**
- Real-time response streaming for better user experience
- Chunk-by-chunk processing for long responses
- Progress indication during generation

#### **Structured Output**
- JSON schema validation for responses
- Pydantic model integration
- Type-safe data generation

#### **Developer Role**
- Hierarchical instruction system
- Override capabilities for system prompts
- Enhanced control over AI behavior

#### **Advanced Parameters**
- **Verbosity Control**: Adjust response length (terse/balanced/expansive)
- **Reasoning Effort**: Configure thinking intensity for complex tasks
- **Store Parameter**: Enable/disable conversation persistence
- **Include Parameter**: Selective field inclusion in responses

#### **Safety Enhancements**
- Safe completions instead of hard refusals
- Transparent explanation of limitations
- Alternative suggestions for sensitive queries

## Dependencies

- **conversation**: Core conversation functionality
- **energy**: Energy management integration
- **history**: Historical data access
- **recorder**: Data recording capabilities
- **rest**: REST API integration
- **scrape**: Web scraping capabilities
- **openai**: OpenAI Python client library

## Supported Models

### Current Models
- GPT-4
- GPT-4o & GPT-4o-mini
- GPT-4 Vision
- GPT-3.5 Turbo
- Azure OpenAI models
- Custom OpenAI-compatible endpoints

### Upcoming Models (With Response API)
- **GPT-5**: Advanced reasoning with 272K context window
- **GPT-5-mini**: Efficient variant for faster responses
- **GPT-5-nano**: Ultra-low latency for real-time applications
- **GPT-5-pro**: Maximum capability for complex tasks

### Specialized Models
- **gpt-4o-search-preview**: Optimized for web search
- **gpt-4o-mini-search-preview**: Lightweight search variant

## Safety Features

- **Function Call Limits**: Configurable maximum function calls per conversation
- **User Confirmation**: AI requests confirmation before executing services
- **Context Management**: Automatic context truncation to prevent token overflow
- **Authentication Validation**: Secure API key management

## Troubleshooting

### Common Issues
1. **Authentication Errors**: Verify your API key and base URL
2. **Function Call Failures**: Check entity permissions and service availability
3. **Context Length Errors**: Adjust context threshold or truncation strategy
4. **Model Not Available**: Ensure your OpenAI account has access to the requested model
5. **Assist API Compatibility**: Ensure the integration is properly registered as a conversation agent

### Compatibility Validation
To verify that this integration works correctly with Home Assistant's Assist API:

1. **Check Agent Registration**: Verify the agent appears in the conversation settings
2. **Test Basic Commands**: Try simple voice or text commands
3. **Verify Function Execution**: Test device control commands
4. **Check Response Format**: Ensure responses appear correctly in the conversation interface

### Debug Information
Enable debug logging in your `configuration.yaml`:

```yaml
logger:
  custom_components.extended_openai_conversation: debug
  homeassistant.components.conversation: debug
```

## Development & Contributing

### For Developers
If you're interested in contributing to this integration or understanding how it works, study the official Home Assistant conversation agent implementations:

- **Official OpenAI Integration**: [home-assistant/core/openai_conversation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/openai_conversation)
- **Google Generative AI Integration**: [home-assistant/core/google_generative_ai_conversation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/google_generative_ai_conversation)

### Key Implementation Points
- **AbstractConversationAgent**: Base class that must be extended
- **ConversationResult**: Required return type for all conversation responses
- **IntentResponse**: Standard response format for Home Assistant
- **Function Calling**: OpenAI function calling integration with Home Assistant services

### Contributing
This integration is open source and welcomes contributions:

- **GitHub**: [jekalmin/extended_openai_conversation](https://github.com/jekalmin/extended_openai_conversation)
- **Issues**: Report bugs and request features
- **Pull Requests**: Submit improvements and fixes

**Note**: When contributing, ensure that any changes maintain compatibility with the official Home Assistant conversation system and follow the same patterns used in the core integrations.

## License

This integration is provided under the MIT License.

## Support

- **Documentation**: [GitHub Wiki](https://github.com/jekalmin/extended_openai_conversation)
- **Community**: Home Assistant Community Forum
- **Issues**: [GitHub Issues](https://github.com/jekalmin/extended_openai_conversation/issues)

## Migration Timeline

The Extended OpenAI Conversation integration is actively being upgraded to support the latest OpenAI capabilities:

- **Phase 1**: Response API migration (maintaining backward compatibility)
- **Phase 2**: Web search integration and GPT-5 model support
- **Phase 3**: AI Task entities and enhanced safety features
- **Phase 4**: Full feature parity with official integrations plus extended capabilities

For detailed implementation plans, progress tracking, and technical specifications, please refer to the **[AI Agent Task List](ai_agent_task_list.md)**.

---

*This integration enhances your Home Assistant experience by bringing AI-powered intelligence to your smart home management. With advanced conversation capabilities, image analysis, and automated device control, you can interact with your smart home more naturally and efficiently than ever before.*

*Note: Some features mentioned in this document (such as GPT-5 models and certain Response API capabilities) are based on announced or planned OpenAI features. Actual availability may vary. Always refer to the official OpenAI documentation for the most current information.* 