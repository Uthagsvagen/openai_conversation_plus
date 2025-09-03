# updated integration plan: openai realtime api in home assistant

*This document clarifies routing logic for using OpenAI’s APIs based on input type. Text-based inputs (from UI or keyboard) **always** use the existing OpenAI **Response API**, while **only** voice-based inputs (microphone pipelines, wake-word devices) invoke the OpenAI **Realtime API** for streaming interaction. The Realtime API is used exclusively for live voice conversations; typed queries continue to use the standard HTTP completion endpoint. This distinction is reflected in configuration, internal design, session management, voice pipeline behavior, and testing.*

## configuration options

- **`enable_realtime_api` (voice-only use):** Redefined to *“use OpenAI Realtime API for voice inputs when available.”*  
  - When enabled, **voice** commands stream via the Realtime API.  
  - **Text** queries are unaffected and always use the Response API.  
  - When disabled, all interactions (voice and text) use the standard turn-based flow.
- **ui/documentation updates:** Make the behavior explicit in labels, e.g., *“Use OpenAI Realtime API for voice.”* Document that this setting does not change text routing.
- **default behavior:** Off by default to preserve current behavior unless the user opts in.

## conversation agent design

- **input-type routing:** On each request, detect input modality:
  - **Text input → Response API** (existing chat/completions path).
  - **Voice input → Realtime API** (only if `enable_realtime_api` is true). If disabled, fall back to STT → Response API → TTS.
- **two internal paths:**
  - **text path:** Build prompt/context; call Response API; return text; optionally TTS if needed by client.
  - **voice path:** Start/attach to a Realtime session; stream mic audio in; stream model audio out.
- **consistent function access:** Both paths retain access to the same HA tools: Assist/intent execution and service calls via the integration’s tool/function layer.
- **graceful fallback:** If realtime fails mid-voice interaction, route that request through standard STT/Response/TTS so the user still gets a reply.

## session management

- **separate sessions:** Maintain distinct session state for **voice** (Realtime) and **text** (Response) so they never interfere. No cross-contamination of context between modes.
- **context handling:** Realtime sessions keep their own conversational state; text sessions use existing conversation context. Manage unique IDs per mode/device.
- **lifecycle:** Voice sessions start on wake/mic activation and stop on inactivity or explicit end. Text sessions proceed as usual. Ending one does not affect the other.

## voice pipeline behavior

- **realtime for voice:** With `enable_realtime_api=true`, bypass traditional STT and stream audio directly to OpenAI; stream audio responses back for low-latency, natural dialog (interruptible where possible).
- **fallback to classic pipeline:** If realtime is disabled/unavailable, keep STT → intent/Response API → TTS unchanged.
- **tts branching:** When using realtime, play the model’s audio directly (skip local TTS). When using Response API, generate speech via the configured TTS engine.
- **voice availability:** Realtime code paths are only used when a voice pipeline is active; purely text interactions never invoke realtime.

## testing and validation

- **routing tests:** Verify that text requests always use the Response API even when realtime is enabled; verify that voice requests use Realtime API only when enabled; verify voice falls back to standard path when disabled or on error.
- **session isolation tests:** Run simultaneous text and voice interactions; ensure contexts remain separate and do not bleed across modes.
- **end-to-end voice tests:** With realtime enabled, confirm streaming response starts promptly and supports interruption; simulate network errors to confirm graceful fallback; with realtime disabled, confirm legacy turn-based behavior.
- **toggle tests:** Toggle `enable_realtime_api` on/off and confirm behavior changes only for voice, not text.
- **non-voice environments:** Ensure systems without microphones or voice use continue working exactly as before (text via Response API).

## notes and caveats

- **full-duplex limits:** True simultaneous talk/listen depends on device capabilities and HA pipeline constraints. Implement “pseudo full‑duplex”: detect user speech during playback, stop/attenuate output, and resume listening via the Realtime session.
- **latency, format, and reliability:** Use the official OpenAI Python SDK for the Realtime API to manage WebSocket sessions and events. Convert mic audio to the expected format (e.g., mono PCM at the model’s required rate). Keep the connection warm to reduce startup latency; handle reconnects and timeouts.
- **privacy and cost:** Document that voice audio is sent to OpenAI when realtime is enabled. Encourage users to set usage limits and understand token-based audio costs.
- **backward compatibility:** If users never enable realtime or don’t use voice, the integration behaves exactly as today.

## success criteria

1. Text inputs always use Response API and are unaffected by realtime settings.  
2. Voice inputs use Realtime API when enabled, with low latency and natural flow; otherwise they follow the classic pipeline.  
3. Function/tool access and HA control work identically in both modes.  
4. Sessions for text and voice remain independent with no context bleed.  
5. Graceful fallback ensures voice requests always complete even if realtime fails.
