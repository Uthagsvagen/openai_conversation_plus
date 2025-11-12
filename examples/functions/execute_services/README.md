# Execute Services Function

## Overview
The `execute_services` function allows you to execute Home Assistant services to control devices and automate actions within your smart home.

## Function Type
- **Type**: Native function
- **Name**: `execute_services`

## Supported Formats

The function accepts **TWO** formats for maximum flexibility:

### Format 1: List Format (Recommended for multiple services)
```json
{
  "list": [
    {
      "domain": "light",
      "service": "turn_on",
      "target": {"entity_id": "light.living_room"}
    }
  ]
}
```

### Format 2: Single Service Format (Auto-wrapped)
```json
{
  "domain": "light",
  "service": "turn_on",
  "target": {"area_id": ["kitchen"]}
}
```

**Note:** When using Format 2, the function automatically wraps the single service call into the list format internally.

## Parameters

### List Format Parameters
- **list** (array): An array of service execution objects

### Single Service Format Parameters
- **domain** (string): The domain of the service (e.g., "light", "switch", "climate")
- **service** (string): The specific service to call (e.g., "turn_on", "turn_off", "set_temperature")
- **target** (object, optional): Target specification for the service
- **service_data** (object, optional): Additional data for the service

### Service Object Properties
Each service call (in list or single format) can contain:

- **domain** (string, required): The domain of the service
- **service** (string, required): The specific service to call
- **target** (object, optional): Target specification with one of:
  - **entity_id** (string or array): Specific entity ID(s)
  - **area_id** (string or array): Area ID(s) to control all devices in that area
  - **area_name** (string or array): Area name(s) to control all devices in that area
  - **device_id** (string or array): Specific device ID(s)
- **service_data** (object, optional): Additional configuration data for the service
- **data** (object, optional): Alternative to service_data (both are supported)

## Example Usage

### Example 1: Turn on a light (List format)
```json
{
  "list": [
    {
      "domain": "light",
      "service": "turn_on",
      "target": {
        "entity_id": "light.living_room"
      }
    }
  ]
}
```

### Example 2: Turn off lights in a room (Single format)
```json
{
  "domain": "light",
  "service": "turn_off",
  "target": {
    "area_id": ["kitchen"]
  }
}
```

### Example 3: Control multiple devices (List format)
```json
{
  "list": [
    {
      "domain": "light",
      "service": "turn_off",
      "target": {
        "area_id": ["kitchen"]
      }
    },
    {
      "domain": "switch",
      "service": "turn_on",
      "target": {
        "entity_id": "switch.coffee_maker"
      }
    },
    {
      "domain": "climate",
      "service": "set_temperature",
      "target": {
        "entity_id": "climate.living_room"
      },
      "service_data": {
        "temperature": 22
      }
    }
  ]
}
```

### Example 4: Control all lights in multiple rooms
```json
{
  "list": [
    {
      "domain": "light",
      "service": "turn_on",
      "target": {
        "area_id": ["living_room", "kitchen"]
      },
      "service_data": {
        "brightness_pct": 80
      }
    }
  ]
}
```

## Common Use Cases
- Control lights, switches, and other smart devices
- Adjust climate settings
- Trigger automation sequences
- Control media players
- Manage security systems

## Notes
- Ensure the entity_id exists in your Home Assistant instance
- The service must be available for the specified domain
- Some services may require additional parameters beyond entity_id
