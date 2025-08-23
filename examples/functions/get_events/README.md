# Get Events Function

## Overview
The `get_events` function retrieves calendar events from multiple calendars within a specified date and time range.

## Function Type
- **Type**: Script function
- **Name**: `get_events`

## Parameters

### Required Parameters
- **start_date_time** (string): The start date and time in ISO 8601 format (`%Y-%m-%dT%H:%M:%S%z`)
- **end_date_time** (string): The end date and time in ISO 8601 format (`%Y-%m-%dT%H:%M:%S%z`)

## How It Works
This function uses the `calendar.get_events` service to:
1. Query multiple calendars for events within the specified time range
2. Store the results in the `_function_result` response variable
3. Return all matching events from the configured calendar entities

## Example Usage

```yaml
# Get today's events
{
  "start_date_time": "2024-01-15T00:00:00+00:00",
  "end_date_time": "2024-01-15T23:59:59+00:00"
}

# Get weekend events
{
  "start_date_time": "2024-01-20T00:00:00+00:00",
  "end_date_time": "2024-01-21T23:59:59+00:00"
}

# Get events for next week
{
  "start_date_time": "2024-01-22T00:00:00+00:00",
  "end_date_time": "2024-01-28T23:59:59+00:00"
}
```

## Calendar Sources
The function queries the following calendar entities:
- `calendar.school_calendar` - Academic schedule
- `calendar.personal_calendar` - Personal appointments
- `calendar.holidays` - Public holidays
- `calendar.sports_calendar` - Sports activities
- `calendar.family_calendar` - Family events

## Response Format
Events are returned in the `_function_result` variable containing:
- Event titles and descriptions
- Start and end times
- Calendar source information
- Event details and metadata

## Common Use Cases
- Checking daily schedules
- Planning weekend activities
- Reviewing upcoming appointments
- Coordinating family events
- Checking school schedules
- Holiday planning

## Requirements
- Calendar integration must be configured
- All specified calendar entities must exist and be accessible
- Proper date/time formatting is required
- Calendar entities must have events within the specified range

## Notes
- Use ISO 8601 format for date/time parameters
- Include timezone information for accurate results
- The function will return events from all configured calendars
- Empty results indicate no events in the specified time range
