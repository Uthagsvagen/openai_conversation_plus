# Get Items from List Function

## Overview
The `get_items_from_list` function allows you to retrieve all active (uncompleted) items from either a shopping list or a to-do list within Home Assistant.

## Function Type
- **Type**: Script function
- **Name**: `get_items_from_list`

## Parameters

### Required Parameters
- **list** (string): The entity ID of the list to read

### List Options
The `list` parameter accepts one of these predefined values:
- `todo.shopping_list` - Read items from the shopping list
- `todo.to_do` - Read items from the to-do list

## How It Works
This function uses the `todo.get_items` service to:
1. Query the specified list for all active items
2. Filter for items with status 'needs_action' (uncompleted)
3. Store the results in the `_function_result` response variable
4. Return all pending items from the list

## Example Usage

```yaml
# Get all shopping list items
{
  "list": "todo.shopping_list"
}

# Get all to-do list items
{
  "list": "todo.to_do"
}
```

## Response Format
Items are returned in the `_function_result` variable containing:
- Item names and descriptions
- Item status information
- List metadata
- Item ordering information

## List Types

### Shopping List (`todo.shopping_list`)
- Retrieve grocery items to purchase
- Check household supplies needed
- Plan shopping trips
- Review pending purchases

### To-Do List (`todo.to_do`)
- View pending tasks and chores
- Check daily activities
- Review project milestones
- Plan upcoming work

## Common Use Cases
- Reviewing shopping lists before going to the store
- Checking daily task progress
- Planning weekend activities
- Coordinating family tasks
- Project management
- Household maintenance planning

## Requirements
- Todo integration must be configured
- The specified list entity must exist and be accessible
- List must contain items to retrieve
- Proper permissions to read lists

## Notes
- Only returns uncompleted items (status: 'needs_action')
- Completed items are filtered out automatically
- The function returns all active items, not just a subset
- Empty results indicate all items are completed or the list is empty
