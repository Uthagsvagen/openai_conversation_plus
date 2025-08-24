# Send SMS by Name Function

## Overview
The `send_sms_by_name` function allows you to send SMS messages to contacts by looking up their phone number using their name from a contact list sensor.

## Function Type
- **Type**: Script function
- **Name**: `send_sms_by_name`

## Parameters

### Required Parameters
- **contact_name** (string): The name of the contact to whom the SMS should be sent
- **message** (string): The message content to send

## How It Works
This function:
1. Looks up the contact's phone number from `sensor.contact_list` using their name
2. Sends the SMS via the `rest_command.send_sms` service
3. Provides feedback if the contact is not found

## Example Usage

```yaml
# Send a simple message
{
  "contact_name": "Friend A",
  "message": "Hello! How are you doing today?"
}

# Send an urgent message
{
  "contact_name": "Emergency Contact",
  "message": "Please call me immediately. It's urgent."
}

# Send a reminder
{
  "contact_name": "Meeting Partner",
  "message": "Don't forget about our meeting tomorrow at 2 PM."
}
```

## Contact Lookup Process
The function searches through the contacts stored in `sensor.contact_list`:
- Parses the JSON contact data
- Finds the contact by matching the name
- Extracts the cellphone number
- Sends the SMS to that number

## Error Handling
If the contact is not found, the function will:
- Respond with an error message
- Suggest checking the spelling
- Recommend adding the contact to the contact list

## Common Use Cases
- Sending reminders to family members
- Emergency notifications
- Meeting confirmations
- Daily check-ins
- Automated alerts

## Requirements
- `sensor.contact_list` must contain contact information in JSON format
- Each contact should have `name` and `cellphone` attributes
- `rest_command.send_sms` service must be configured
- Contact names must match exactly (case-sensitive)

## Notes
- Ensure contact names are spelled correctly
- The contact list sensor should be updated when adding new contacts
- SMS delivery depends on your configured SMS service
