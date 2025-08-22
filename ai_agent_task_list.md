# AI Agent Task List - Extended OpenAI Conversation Integration Upgrade

## Overview
This task list outlines the work required to upgrade the Extended OpenAI Conversation integration to support the latest OpenAI features, including the Response API, GPT-5 models, web search capabilities, and AI Task entities.

## Task List

### 1. Migrate from ChatCompletions API to Response API ⚡

**Background:**
The OpenAI Responses API is a superset of the Chat Completions API, designed to replace both Chat Completions and the deprecated Assistants API (EOL H1 2026). It provides a unified interface with enhanced capabilities.

**Key Features to Implement:**
- **Backward Compatibility**: Ensure existing Chat Completions code continues to work
- **Built-in Tools**: 
  - `web_search_preview` - Real-time web search
  - `file_search` - Search within uploaded files
  - `computer_use` - Control computer interfaces (future consideration)
- **State Management**: Optional server-side conversation persistence using `previous_response_id`
- **Multi-tool Orchestration**: Execute multiple tools in a single API call
- **Multimodal Support**: Handle text + image inputs seamlessly

**Implementation Steps:**
1. Update OpenAI client initialization to support Responses API
2. Modify `async_process` method in `OpenAIAgent` class to use `client.responses.create()`
3. Add support for `previous_response_id` parameter for conversation continuity
4. Implement tool selection logic for automatic tool usage
5. Update response parsing to handle new response format
6. Maintain backward compatibility with existing Chat Completions calls

**Code Changes Required:**
- `__init__.py`: Update API calls from `client.chat.completions.create()` to `client.responses.create()`
- Add new configuration options for Response API features
- Update response handling to support new output format

**References:**
- [OpenAI Responses API Documentation](https://platform.openai.com/docs/api-reference/responses)
- Migration guides suggest minimal code changes due to backward compatibility

---

### 2. Add Support for GPT-5 and GPT-5-mini Models 🤖

**Background:**
GPT-5 was announced on August 7, 2025 (hypothetical future date from research), representing a significant advancement in AI capabilities with PhD-level expertise across domains.

**Model Specifications:**
- **GPT-5**: 
  - Context: 272,000 tokens input (~200,000 words)
  - Output: 128,000 tokens
  - Pricing: $1.25 per 1M input tokens, $10 per 1M output tokens
- **GPT-5-mini**: 
  - Optimized for efficiency
  - Pricing: $0.25 per 1M input tokens, $2 per 1M output tokens
- **Additional Variants**: gpt-5-nano (ultra-low latency), gpt-5-pro (maximum capability)

**Key Features:**
- Unified intelligence system with automatic model routing
- Four reasoning levels: minimal, low, medium, high
- 94.6% accuracy on AIME 2025 (100% with Python tools)
- 65% fewer hallucinations compared to previous models
- Safe completions instead of hard refusals

**Implementation Steps:**
1. Add new model constants to `const.py`:
   ```python
   GPT5_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro"]
   ```
2. Update model selection in configuration flow
3. Add reasoning level configuration option
4. Implement personality modes (Cynic, Robot, Listener, Nerd)
5. Update pricing calculations for new models

**Configuration Updates:**
- Add reasoning_effort parameter (minimal/low/medium/high)
- Add verbosity control (terse/balanced/expansive)
- Update model dropdown in config flow to include GPT-5 variants

---

### 3. Implement Web Search Capability 🔍

**Background:**
The Responses API includes built-in web search via the `web_search_preview` tool, eliminating the need for custom implementations.

**Features to Implement:**
- **Automatic Search Triggering**: Model decides when web search is needed
- **Citation Support**: Automatically includes source URLs in responses
- **Location-Based Search**: Support for geographic context
- **Search Context Control**: Configurable depth of search (low/medium/high)

**Implementation Steps:**
1. Add web search configuration to options flow:
   ```python
   CONF_ENABLE_WEB_SEARCH = "enable_web_search"
   CONF_SEARCH_CONTEXT_SIZE = "search_context_size"
   CONF_USER_LOCATION = "user_location"
   ```

2. Update `async_process` to include web search tool:
   ```python
   tools = []
   if self.entry.options.get(CONF_ENABLE_WEB_SEARCH, False):
       tools.append({
           "type": "web_search_preview",
           "search_context_size": self.entry.options.get(CONF_SEARCH_CONTEXT_SIZE, "medium"),
           "user_location": self._get_user_location()
       })
   ```

3. Add citation parsing from response annotations
4. Create helper method for location configuration
5. Update UI strings for new configuration options

**Configuration UI:**
- Toggle: "Enable Web Search"
- Dropdown: "Search Context Size" (low/medium/high)
- Optional: Location settings (country, city, region)

**Note**: Currently requires models `gpt-4o-search-preview` or `gpt-4o-mini-search-preview` for Chat Completions, or standard models with Responses API.

---

### 4. Integrate AI Task Support 🎯

**Background:**
The official Home Assistant integrations now include AI Task entities for structured data generation and complex task handling.

**Required Components:**
1. **Entity Base Class**: Create `entity.py` with `OpenAIBaseLLMEntity`
2. **AI Task Platform**: Implement `ai_task.py` (already copied)
3. **Platform Registration**: Update `__init__.py` to register AI task platform
4. **Manifest Updates**: Add ai_task to dependencies

**Implementation Steps:**
1. Create `entity.py`:
   ```python
   from homeassistant.helpers.entity import Entity
   
   class OpenAIBaseLLMEntity(Entity):
       """Base class for OpenAI LLM entities."""
       
       async def _async_handle_chat_log(self, chat_log, task_name, structure):
           """Handle conversation log and generate response."""
           # Implementation needed
   ```

2. Update `__init__.py` to add platform setup:
   ```python
   PLATFORMS = ["ai_task"]
   
   async def async_setup_entry(hass, entry):
       # ... existing code ...
       await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
   ```

3. Implement `_async_generate_data` method in `OpenAITaskEntity`
4. Add support for structured output with JSON schemas
5. Handle attachments and multimodal inputs

**Features Supported:**
- `GenDataTask`: Generate structured data from prompts
- Attachment support for images and documents
- JSON schema validation for structured outputs
- Integration with conversation component

---

### 5. Add Missing Features from Official Integrations 🔧

**Features to Add:**

1. **Prompts API Support**
   - Centralized prompt management
   - Version control for system prompts
   - A/B testing capabilities

2. **Enhanced Streaming**
   ```python
   stream = await client.responses.create(
       model="gpt-4o",
       input=messages,
       stream=True
   )
   
   for event in stream:
       if hasattr(event, "type") and "text.delta" in event.type:
           # Process streaming chunk
   ```

3. **Response Format Configuration**
   - Support for `json_object` format
   - Structured output with Pydantic models
   - Custom response schemas

4. **Developer Role Support**
   - Hierarchical instruction system
   - Override system prompts with developer role
   - Chain of command implementation

5. **Additional Parameters**
   - `verbosity`: Control response length
   - `reasoning_effort`: Adjust thinking intensity
   - `store`: Enable/disable conversation persistence
   - `include`: Selective field inclusion in responses

6. **Truncation Strategy**
   - Automatic context management when exceeding limits
   - Configurable truncation methods
   - Token counting and optimization

**Implementation Priority:**
1. Streaming support (High - improves UX)
2. Response format (High - enables structured data)
3. Developer role (Medium - advanced feature)
4. Additional parameters (Medium - nice to have)
5. Prompts API (Low - future enhancement)

---

### 6. Implement Enhanced Safety Features 🛡️

**GPT-5 Safety Enhancements:**
- **Safe Completions**: Provide helpful information within safety boundaries
- **Transparent Refusals**: Explain why certain requests cannot be fulfilled
- **Alternative Suggestions**: Offer safe alternatives for sensitive queries
- **Dual-use Navigation**: Better handling of biology, cybersecurity topics

**Implementation:**
1. Update prompt templates to include safety guidelines
2. Add configuration for safety level (strict/balanced/relaxed)
3. Implement refusal explanation parser
4. Create alternative suggestion generator

---

### 7. Update Documentation 📚

**Documentation Updates Required:**

1. **agent.md**
   - Add Response API migration guide
   - Document GPT-5 model capabilities
   - Explain web search configuration
   - Add AI Task entity examples

2. **README.md**
   - Update feature list
   - Add new configuration options
   - Include migration notes

3. **strings.json / translations**
   - Add new configuration labels
   - Update option descriptions
   - Translate new features

4. **Examples**
   - Web search automation example
   - AI Task entity usage
   - GPT-5 with reasoning levels
   - Multi-tool usage patterns

---

## Migration Considerations

### Breaking Changes
- None expected due to Response API backward compatibility
- Existing configurations should continue working

### Performance Improvements
- Response API ~2x faster than Assistants API
- Reduced latency with unified tool calls
- Better token efficiency with GPT-5

### Cost Implications
- Web search incurs additional costs
- GPT-5 pricing varies by model variant
- Monitor usage with new features enabled

---

## Testing Requirements

1. **Unit Tests**
   - Response API compatibility
   - Web search integration
   - AI Task entity functionality
   - Model selection logic

2. **Integration Tests**
   - End-to-end conversation flow
   - Multi-tool orchestration
   - Citation parsing
   - Streaming response handling

3. **Manual Testing**
   - Configuration UI changes
   - Web search results quality
   - GPT-5 model performance
   - Safety feature validation

---

## Timeline Estimate

- **Week 1**: Response API migration and basic testing
- **Week 2**: GPT-5 model support and web search
- **Week 3**: AI Task integration and missing features
- **Week 4**: Safety features, documentation, and testing

---

## Resources and References

### Official Documentation
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [Home Assistant Conversation Development](https://developers.home-assistant.io/docs/core/entity/conversation/)
- [OpenAI Web Search Guide](https://platform.openai.com/docs/guides/tools-web-search)

### Source Code References
- [Official OpenAI Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/openai_conversation)
- [Google Generative AI Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/google_generative_ai_conversation)

### Community Resources
- [OpenAI Developer Community](https://community.openai.com/)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

---

*Note: This task list is based on research conducted on available information. Some features like GPT-5 may be hypothetical or future releases. Always refer to official OpenAI documentation for the most current information.* 