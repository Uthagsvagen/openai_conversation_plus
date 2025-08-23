# Add Item to List Function

## Overview
The `add_item_to_list` function allows you to add items to either a shopping list or a to-do list within Home Assistant.

## Function Type
- **Type**: Script function
- **Name**: `add_item_to_list`

## Parameters

### Required Parameters
- **item** (string): The item to be added to the list
- **list** (string): The entity ID of the list to update

### List Options
The `list` parameter accepts one of these predefined values:
- `todo.shopping_list` - Add items to the shopping list
- `todo.to_do` - Add items to the to-do list

## How It Works
This function uses the `todo.add_item` service to:
1. Add the specified item to the chosen list
2. The item will appear as a new, unchecked entry
3. Items are added to the end of the list

## Example Usage

```yaml
# Add item to shopping list
{
  "item": "Milk",
  "list": "todo.shopping_list"
}

# Add task to to-do list
{
  "item": "Call the dentist",
  "list": "todo.to_do"
}

# Add grocery item
{
  "item": "Bread",
  "list": "todo.shopping_list"
}

# Add household task
{
  "item": "Clean the garage",
  "list": "todo.to_do"
}
```

## List Types

### Shopping List (`todo.shopping_list`)
- Ideal for grocery shopping
- Track household supplies
- Plan shopping trips
- Share with family members

### To-Do List (`todo.to_do`)
- Track tasks and chores
- Manage daily activities
- Plan projects
- Set reminders

## Common Use Cases
- Grocery shopping preparation
- Household task management
- Project planning
- Daily activity tracking
- Family coordination
- Task delegation

## Requirements
- Todo integration must be configured
- Both list entities must exist and be accessible
- Proper permissions to modify lists

## Notes
- Items are added as unchecked/not completed
- Lists maintain the order items were added
- Items can be manually reordered in the Home Assistant interface
- The function only adds items, it doesn't check for duplicates
