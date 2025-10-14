# Function Calling and MCP Server Integration Fixes

## Summary

Fixed critical bugs preventing function calling and MCP server integration from working with the OpenAI Responses API. These changes enable:

✅ Custom functions (like `execute_services`) to work correctly  
✅ MCP servers to be callable by the model  
✅ Streaming function calls to execute in real-time  
✅ Non-streaming function calls with proper execution loops  
✅ Multiple sequential tool calls to work  
✅ Model to generate proper responses after tool execution

## Changes Made

### 1. Fixed Tool Definition Structure

**Issue**: Tools were being defined in Chat Completions format with nested structure, which the Responses API doesn't recognize correctly.

**Files Modified**:
- `custom_components/openai_conversation_plus/conversation.py` (lines 120-167)
- `custom_components/openai_conversation_plus/__init__.py` (lines 331-359)

**Changes**:
```python
# BEFORE (Chat Completions format - WRONG):
{
    "type": "function",
    "function": {
        "name": "execute_services",
        "description": "...",
        "parameters": {...}
    }
}

# AFTER (Responses API format - CORRECT):
{
    "type": "function",
    "name": "execute_services",
    "description": "...",
    "parameters": {...}
}
```

### 2. Implemented Function Execution Loop (Non-Streaming)

**Issue**: After the model made function calls, the code executed them but never sent the results back to get a final response.

**File Modified**: `custom_components/openai_conversation_plus/conversation.py` (lines 381-510)

**Changes**:
- Added a proper execution loop (max 10 iterations)
- Execute all function calls from response
- Format function outputs correctly as `function_call_output` items
- Send outputs back to the model for continued reasoning
- Loop until model returns final text response (no more function calls)

**Flow**:
```
1. Send initial request with tools
2. Get response with function calls
3. Execute all function calls
4. Append outputs to conversation
5. Send back to model
6. Repeat until no more function calls
7. Return final text response to user
```

### 3. Fixed Streaming Event Names

**Issue**: Using incorrect event type names that don't match the official Responses API documentation.

**File Modified**: `custom_components/openai_conversation_plus/conversation.py` (lines 288-384)

**Changes**:
```python
# BEFORE (WRONG event names):
- response.function_call.arguments.delta
- response.function_call.arguments.done

# AFTER (CORRECT event names per docs):
- response.output_item.added (detect function call start)
- response.function_call_arguments.delta (accumulate arguments)
- response.function_call_arguments.done (execute function)
```

**Improvements**:
- Properly track function calls by `item_id`
- Accumulate arguments incrementally
- Execute functions when arguments are complete
- Support both custom functions and HA LLM API tools

### 4. Verified MCP Tool Structure

**Issue**: Needed verification that MCP tools use correct Responses API format.

**Files Checked**:
- `custom_components/openai_conversation_plus/__init__.py` (lines 232-328, 373-389)

**Result**: MCP tool structure was already correct:
```python
{
    "type": "mcp",
    "server_label": "my_server",
    "server_url": "https://...",
    "server_api_key": "...",  # optional
    "allowed_tools": [...],    # optional
    "require_approval": "never" # optional
}
```

## Testing Instructions

### Test Custom Functions (execute_services)

1. **Configure a custom function** in Home Assistant integration options:
```yaml
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
              domain:
                type: string
              service:
                type: string
              service_data:
                type: object
  function:
    type: native
```

2. **Test with a command**:
   - "Turn on the living room light"
   - "Set the thermostat to 22 degrees"
   - "Turn on multiple lights in the kitchen"

3. **Expected behavior**:
   - Model recognizes it needs to call `execute_services`
   - Function executes the Home Assistant service
   - Model confirms the action was completed

### Test MCP Servers

1. **Configure an MCP server** in integration options:
```yaml
mcp_servers:
  weather_api:
    server_url: https://api.example.com/mcp
    server_api_key: your_key_here
    allowed_tools:
      - get_weather
      - get_forecast
    require_approval: never
```

2. **Test with a command**:
   - "What's the weather like today?"
   - Model should call the MCP server's `get_weather` tool

3. **Expected behavior**:
   - Model recognizes the MCP tool is available
   - Calls the tool with appropriate arguments
   - Receives the response
   - Generates a natural language answer

### Test Streaming Function Calls

1. **Enable streaming** in integration options (should be enabled by default)

2. **Send a command** that requires a function call:
   - "Turn on the bedroom light"

3. **Expected behavior**:
   - You should see the function being called in real-time
   - Service executes immediately
   - Model streams the confirmation response

### Test Multiple Sequential Function Calls

1. **Send a complex command** requiring multiple actions:
   - "Turn on all the lights in the living room and set the temperature to 21 degrees"

2. **Expected behavior**:
   - Model calls multiple functions in sequence
   - All services execute
   - Model confirms all actions were completed

## Debug Logging

To see detailed function calling logs, check Home Assistant logs for entries with `[v...]` prefix:

```
[v1.x.x] Loading user-defined functions from options: 1 found
[v1.x.x]   - Added function: execute_services
[v1.x.x] Sending 5 tools to OpenAI (stream=True, tool_choice=auto)
[v1.x.x] Executing function: execute_services
[v1.x.x] Function execute_services executed successfully
[v1.x.x] Parsed final response text: I've turned on the living room light.
```

## Known Limitations

1. **Streaming with multiple turns**: Current implementation executes functions during streaming but doesn't automatically continue streaming after function execution. Complex multi-turn scenarios may fall back to non-streaming mode.

2. **Reasoning tokens**: GPT-5 and other reasoning models may use reasoning tokens which are not directly visible in the response but are included in token counts.

3. **Error handling**: Function execution errors are caught and logged but may not always result in user-friendly error messages.

## Next Steps

Potential future enhancements:

1. **Implement streaming multi-turn loops**: Allow streaming to continue after function execution without falling back to non-streaming.

2. **Better error messages**: Improve user-facing error messages when function calls fail.

3. **Function call confirmation**: Add optional user confirmation before executing sensitive functions.

4. **Parallel function execution**: Execute independent function calls in parallel for better performance.

5. **Function call history**: Store and display function call history for debugging.

## References

- [OpenAI Responses API Documentation](https://platform.openai.com/docs/api-reference/responses)
- [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [Handling Function Calls with Reasoning Models](https://platform.openai.com/docs/guides/reasoning)
- [Home Assistant LLM API Documentation](https://developers.home-assistant.io/docs/core/llm/)

