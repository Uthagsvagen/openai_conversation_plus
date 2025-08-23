# Remove Item from List Function

## Overview
The `remove_item_from_list` function allows you to mark items as completed and remove them from either a shopping list or a to-do list within Home Assistant.

## Function Type
- **Type**: Script function
- **Name**: `remove_item_from_list`

## Parameters

### Required Parameters
- **item** (string): The item to be removed from the list
- **list** (string): The entity ID of the list to update

### List Options
The `list` parameter accepts one of these predefined values:
- `todo.shopping_list` - Remove items from the shopping list
- `todo.to_do` - Remove items from the to-do list

## How It Works
This function uses the `todo.update_item` service to:
1. Find the specified item in the chosen list
2. Mark it as completed by setting status to 'completed'
3. The item will be removed from the active list view

## Example Usage

```yaml
# Complete shopping list item
{
  "item": "Milk",
  "list": "todo.shopping_list"
}

# Complete to-do task
{
  "item": "Call the dentist",
  "list": "todo.to_do"
}

# Mark grocery item as purchased
{
  "item": "Bread",
  "list": "todo.shopping_list"
}

# Complete household task
{
  "item": "Clean the garage",
  "list": "todo.to_do"
}
```

## List Types

### Shopping List (`todo.shopping_list`)
- Mark items as purchased
- Remove completed shopping tasks
- Track shopping progress
- Maintain shopping history

### To-Do List (`todo.to_do`)
- Mark tasks as completed
- Remove finished chores
- Track project progress
- Maintain task history

## Common Use Cases
- Marking grocery items as purchased
- Completing household tasks
- Tracking project milestones
- Managing daily activities
- Family task coordination
- Progress monitoring

## Requirements
- Todo integration must be configured
- Both list entities must exist and be accessible
- The specified item must exist in the chosen list
- Proper permissions to modify lists

## Notes
- Items are marked as completed, not permanently deleted
- Completed items may still be visible in list history
- The item name must match exactly (case-sensitive)
- If the item doesn't exist, the function will fail silently
