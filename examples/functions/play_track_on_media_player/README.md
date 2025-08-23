# Play Track on Media Player Function

## Overview
The `play_track_on_media_player` function allows you to play music tracks or playlists on a specified media player using voice commands.

## Function Type
- **Type**: Script function
- **Name**: `play_track_on_media_player`

## Parameters

### Required Parameters
- **media_name** (string): The name of the media to play (track or playlist)
- **media_player** (string): The entity ID of the media player

### Optional Parameters
- **media_type** (string): The type of media (e.g., "track", "playlist"). Defaults to "track" if not specified
- **artist_name** (string): The artist of the track
- **album_name** (string): The album of the track

## Example Usage

```yaml
# Play a specific track
{
  "media_name": "Bohemian Rhapsody",
  "media_player": "media_player.living_room",
  "media_type": "track",
  "artist_name": "Queen"
}

# Play a playlist
{
  "media_name": "Workout Mix",
  "media_player": "media_player.kitchen",
  "media_type": "playlist"
}

# Play with minimal parameters
{
  "media_name": "Jazz Vibes",
  "media_player": "media_player.bedroom"
}
```

## How It Works
This function uses the `music_assistant.play_media` service to:
1. Search for the specified media by name
2. Apply optional filters for artist and album
3. Play the media on the specified media player
4. Default to "track" type if media_type is not specified

## Common Use Cases
- Voice-controlled music playback
- Playing specific songs or albums
- Queueing playlists
- Multi-room audio control
- Background music for activities

## Requirements
- Music Assistant integration must be installed and configured
- The specified media player must be available
- Media must exist in your Music Assistant library

## Notes
- The function will search for media by name, so be specific with titles
- Artist and album names help narrow down the search
- Media type defaults to "track" for single songs
