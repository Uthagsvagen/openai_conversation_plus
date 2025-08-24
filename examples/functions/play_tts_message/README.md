# Play TTS Message Function

## Overview
The `play_tts_message` function allows you to respond to questions by converting text to speech and playing it on a specified media player.

## Function Type
- **Type**: Script function
- **Name**: `play_tts_message`

## Parameters

### Required Parameters
- **message** (string): The text message to be converted to speech and played
- **media_player** (string): The entity ID of the media player where the message will be played

## How It Works
This function uses the `tts.speak` service to:
1. Convert the provided text message to speech
2. Play the audio on the specified media player
3. Disable caching to ensure fresh audio generation

## Example Usage

```yaml
# Simple TTS message
{
  "message": "Hello! The weather today is sunny with a high of 24 degrees.",
  "media_player": "media_player.room_a"
}

# Time announcement
{
  "message": "It's currently 3:30 PM. Time for your afternoon meeting.",
  "media_player": "media_player.room_b"
}

# Status update
{
  "message": "Your laundry is finished. Please check the washing machine.",
  "media_player": "media_player.room_c"
}
```

## TTS Configuration
The function uses the `tts.openai_tts_gpt_4o_mini_tts` service with:
- **Cache**: Disabled (false) for fresh audio generation
- **Target**: The specified media player entity
- **Message**: The text to convert to speech

## Common Use Cases
- Voice announcements and notifications
- Reading out weather updates
- Time and schedule reminders
- Status updates for smart home devices
- Interactive voice responses
- Accessibility features

## Requirements
- OpenAI TTS integration must be configured
- The specified media player must be available and working
- TTS service must have proper API credentials

## Notes
- TTS generation may take a few seconds depending on message length
- Audio quality depends on your TTS service configuration
- Ensure the media player volume is set appropriately
- The function will override any currently playing media on the target device
