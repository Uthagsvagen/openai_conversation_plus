# OpenAI Realtime API Integration Plan for Home Assistant

## 🎯 Objective
Integrate OpenAI Realtime API into the Home Assistant OpenAI Conversation Plus integration to enable non-turn-based, interruption-capable voice interactions while maintaining all existing tools, MCP, and function capabilities.

## 📊 Feasibility Analysis

### ✅ What's Possible
1. **Custom Conversation Agent**: We already have a conversation entity that can be extended
2. **WebSocket Support**: Home Assistant supports WebSocket connections for real-time communication
3. **Intent Execution**: Can programmatically execute HA intents from within the integration
4. **Function Calling**: Realtime API supports function calling, compatible with our existing tools
5. **Audio Streaming**: HA has audio stream capabilities through its media/tts components

### ⚠️ Challenges
1. **Voice Pipeline Integration**: HA's voice pipeline expects discrete STT→Intent→TTS steps
2. **Audio Handling**: Need to handle raw audio streams within the conversation agent
3. **Wake Word Bridge**: Need to connect wake word detection to WebSocket session
4. **Session Management**: Realtime API uses persistent WebSocket sessions vs request-response

### 🔧 Technical Approach
- Create a hybrid conversation agent that supports both text (Responses API) and audio (Realtime API)
- Implement WebSocket client for Realtime API within the integration
- Bridge Realtime API function calls to HA intent system
- Use HA's assist API as an intermediary for device control

## 📝 Implementation TODO List

### Phase 1: Foundation Setup

#### 1. Research & Architecture Design
- [ ] Study HA voice pipeline architecture in detail
- [ ] Analyze how wake word detection triggers pipeline
- [ ] Research HA's audio stream handling capabilities
- [ ] Document WebSocket integration patterns in HA
- [ ] Design session management for persistent connections

#### 2. Configuration Schema Updates
- [ ] Add `CONF_ENABLE_REALTIME_API` boolean option
- [ ] Add `CONF_REALTIME_MODEL` selection (e.g., "gpt-4o-realtime")
- [ ] Add `CONF_REALTIME_VOICE` selection
- [ ] Add `CONF_REALTIME_MODALITIES` (text, audio)
- [ ] Add `CONF_REALTIME_INSTRUCTIONS` for system prompt
- [ ] Update config_flow.py with new options
- [ ] Update strings.json and translations

### Phase 2: Core Realtime API Client

#### 3. WebSocket Client Implementation
- [ ] Create `realtime_client.py` for WebSocket management
- [ ] Implement connection establishment with auth
- [ ] Handle connection lifecycle (connect, reconnect, disconnect)
- [ ] Implement message queuing for reliability
- [ ] Add heartbeat/ping-pong for connection health

#### 4. Audio Stream Handling
- [ ] Create `audio_handler.py` for audio processing
- [ ] Implement audio format conversion (PCM16 24kHz mono)
- [ ] Handle audio chunk buffering and streaming
- [ ] Implement audio input stream from HA
- [ ] Implement audio output stream to HA

#### 5. Realtime Session Management
- [ ] Create `realtime_session.py` for session state
- [ ] Implement session creation and configuration
- [ ] Handle session.update for dynamic changes
- [ ] Manage conversation state and history
- [ ] Implement session cleanup and resource management

### Phase 3: Integration with Home Assistant

#### 6. Voice Pipeline Integration
- [ ] Create custom pipeline component or adapter
- [ ] Override/bypass STT step when using Realtime API
- [ ] Override/bypass TTS step when using Realtime API
- [ ] Connect wake word detection to session start
- [ ] Handle voice activity detection (VAD) events

#### 7. Conversation Agent Enhancement
- [ ] Extend `conversation.py` to support audio mode
- [ ] Add `async_process_audio` method for audio input
- [ ] Implement mode switching (text vs audio)
- [ ] Handle interruption events
- [ ] Manage turn detection and conversation flow

#### 8. Tool & Function Bridge
- [ ] Convert existing functions to Realtime API format
- [ ] Implement assist intent wrapper function
- [ ] Bridge MCP tools to Realtime function calls
- [ ] Handle function call responses in audio context
- [ ] Implement error handling for function calls

### Phase 4: Assist API Integration

#### 9. Assist Function Implementation
- [ ] Create `assist_function.py` for HA assist bridge
- [ ] Implement function spec for assist calls
- [ ] Parse natural language to assist intents
- [ ] Handle entity state queries through assist
- [ ] Execute device control through assist
- [ ] Return results in conversational format

#### 10. Context Management
- [ ] Pass HA context to Realtime API session
- [ ] Include exposed entities in instructions
- [ ] Update context on state changes
- [ ] Handle area/room awareness
- [ ] Implement user preferences

### Phase 5: Advanced Features

#### 11. Interruption Handling
- [ ] Detect user interruptions in audio stream
- [ ] Cancel ongoing responses appropriately
- [ ] Handle context switching mid-conversation
- [ ] Implement "barge-in" support

#### 12. Continuous Conversation
- [ ] Remove turn-based constraints
- [ ] Handle overlapping speech
- [ ] Implement natural pauses vs end-of-turn
- [ ] Support follow-up questions without wake word

#### 13. Multi-Modal Support
- [ ] Handle mixed text/audio inputs
- [ ] Support visual responses (if applicable)
- [ ] Implement fallback to text mode
- [ ] Handle mode switching dynamically

### Phase 6: Testing & Optimization

#### 14. Testing Suite
- [ ] Unit tests for WebSocket client
- [ ] Integration tests with mock Realtime API
- [ ] End-to-end voice interaction tests
- [ ] Performance benchmarks
- [ ] Error recovery tests

#### 15. Optimization
- [ ] Optimize audio buffering for latency
- [ ] Implement connection pooling
- [ ] Add caching for frequently used intents
- [ ] Optimize memory usage for long sessions
- [ ] Add metrics and monitoring

### Phase 7: Documentation & Release

#### 16. Documentation
- [ ] Update README with Realtime API features
- [ ] Create setup guide for voice configuration
- [ ] Document supported voice commands
- [ ] Add troubleshooting section
- [ ] Create example configurations

#### 17. Migration & Compatibility
- [ ] Ensure backward compatibility
- [ ] Create migration guide
- [ ] Test with existing configurations
- [ ] Validate all existing features still work
- [ ] Handle graceful degradation

## 🏗️ Technical Implementation Details

### WebSocket Connection Flow
```
Wake Word → Start Session → Connect WebSocket → Stream Audio ↔ Receive Responses → Execute Functions → End Session
```

### Function Call Flow
```
User Speech → Realtime API → Function Call → Assist Bridge → HA Intent → Device Action → Response
```

### Audio Pipeline
```
Microphone → Audio Stream → WebSocket → OpenAI → Response Audio → Speaker
                                ↓
                          Function Calls → HA Assist
```

## 🔑 Key Components to Create

1. **realtime_client.py** - WebSocket client for Realtime API
2. **audio_handler.py** - Audio stream processing
3. **realtime_session.py** - Session management
4. **assist_function.py** - Bridge to HA assist
5. **realtime_conversation.py** - Extended conversation agent

## ⚡ Configuration Example
```yaml
enable_realtime_api: true
realtime_model: "gpt-4o-realtime-preview"
realtime_voice: "nova"
realtime_modalities: ["text", "audio"]
realtime_instructions: |
  You are a helpful home assistant. Use the assist function to:
  - Query device states
  - Control devices
  - Answer questions about the home
```

## 🚧 Proof of Concept Steps

1. **Minimal WebSocket Client**: Test basic connection to Realtime API
2. **Audio Echo Test**: Stream audio in and get audio out
3. **Simple Function Call**: Test assist function with hardcoded intent
4. **Integration Test**: Connect wake word to full flow
5. **Production Ready**: Full implementation with all features

## ⚠️ Risk Mitigation

- **Fallback Mode**: Always have text-based fallback
- **Connection Recovery**: Automatic reconnection on failure
- **Resource Limits**: Implement session timeouts
- **Cost Control**: Monitor and limit API usage
- **Privacy**: Local wake word, cloud processing only after trigger

## 📅 Estimated Timeline

- **Phase 1-2**: 2 weeks (Foundation and core client)
- **Phase 3-4**: 3 weeks (HA integration and assist bridge)
- **Phase 5**: 2 weeks (Advanced features)
- **Phase 6-7**: 1 week (Testing and documentation)

**Total**: ~8 weeks for full implementation

## 🎯 Success Criteria

1. Wake word triggers Realtime API session
2. Continuous conversation without turn-taking
3. Natural interruptions work correctly
4. All existing functions/tools available
5. Assist commands execute properly
6. Audio quality is clear and low-latency
7. Graceful fallback to text mode
8. Works with HA Voice Preview

## 📚 References

- [OpenAI Realtime API Guide](https://platform.openai.com/docs/guides/realtime)
- [Home Assistant Conversation API](https://developers.home-assistant.io/docs/intent_conversation_api)
- [Home Assistant Intent Handling](https://developers.home-assistant.io/docs/intent_handling)
- [Home Assistant LLM API](https://developers.home-assistant.io/docs/core/llm/)
- [ElatoAI Implementation](https://github.com/akdeb/ElatoAI) - Reference for WebSocket handling
