# Get Attributes Function

## Overview
The `get_attributes` function allows you to retrieve the current state and all attributes of any Home Assistant entity.

## Function Type
- **Type**: Template function
- **Name**: `get_attributes`

## Parameters

### Required Parameters
- **entity_id** (string): The entity ID of the Home Assistant entity to query

## How It Works
This function uses a template to:
1. Access the `states` object for the specified entity
2. Return the complete state object including:
   - Current state value
   - All entity attributes
   - Last updated timestamp
   - Entity metadata

## Example Usage

```yaml
# Get light bulb attributes
{
  "entity_id": "light.room_a"
}

# Get sensor data
{
  "entity_id": "sensor.temperature_room_a"
}

# Get device tracker information
{
  "entity_id": "device_tracker.mobile_phone"
}

# Get climate control details
{
  "entity_id": "climate.thermostat"
}
```

## Response Format
The function returns the complete state object containing:
- **state**: Current entity state (e.g., "on", "off", "23.5")
- **attributes**: All entity attributes (e.g., brightness, temperature, location)
- **last_updated**: Timestamp of last state change
- **last_changed**: Timestamp of last meaningful state change
- **context**: User context information

## Common Use Cases
- Checking device status and properties
- Reading sensor values and attributes
- Monitoring device conditions
- Debugging entity configurations
- Data collection and logging
- Conditional automation logic

## Entity Types
This function works with all Home Assistant entity types:
- **Lights**: State, brightness, color, effects
- **Sensors**: Values, units, device class
- **Switches**: State, power consumption
- **Climate**: Temperature, mode, fan speed
- **Media Players**: State, volume, source
- **Device Trackers**: Location, battery, speed

## Requirements
- The specified entity must exist in Home Assistant
- Entity must be accessible and not disabled
- Proper permissions to read entity states

## Notes
- Returns the complete state object, not just attributes
- Use this function when you need both state and attributes
- The response includes all available entity information
- Entity must be online and responding for accurate data
