<!-- 8175f18e-b051-4a32-8a28-4b636ca42693 64bc976d-237a-4bad-b65b-0ac3623b7324 -->
# Update OpenAI Library and Enable Streaming Features

## Current State Analysis

**Current OpenAI Library Requirement:** `openai>=1.101.0` (in manifest.json, requirements.txt, setup.py)

**Latest Available Version:** Need to verify the actual latest version on PyPI (web search indicated 1.90.0, but manifest requires 1.101.0)

**Missing Features:**

1. `parallel_tool_calls: true` not explicitly set in Responses API calls
2. `stream: true` parameter not explicitly set (streaming exists but may not be properly configured)
3. Need to verify reasoning effort and verbosity are configurable in HA UI

## Implementation Plan

### Step 1: Check and Update OpenAI Library Version

- Run `pip list | grep openai` to check currently installed version
- Check PyPI for latest version: `pip index versions openai`
- Update requirements if newer version is available:
  - `manifest.json` (line 22)
  - `requirements.txt` (line 1)
  - `setup.py` (line 29)
- Install/upgrade on local system: `pip install --upgrade openai`

### Step 2: Enable Parallel Tool Calls

**File:** `custom_components/openai_conversation_plus/__init__.py`

**Current code** (lines 661-668) needs to add `parallel_tool_calls`:
response_kwargs = {
    "model": model,
    "input": messages,
    "max_output_tokens": max_tokens,
    "store": ...,
}
**Should be:**
response_kwargs = {
    "model": model,
    "input": messages,
    "max_output_tokens": max_tokens,
    "parallel_tool_calls": True,  # ✅ ADD THIS
    "stream": True,  # ✅ ADD THIS (for non-streaming fallback)
    "store": ...,
}

### Step 3: Ensure Streaming is Properly Configured

**File:** `custom_components/openai_conversation_plus/__init__.py`

The code already has streaming logic (lines 742-771), but we need to:

1. Ensure `stream=True` is always passed in kwargs
2. Verify the streaming implementation handles parallel tool calls correctly
3. Add `parallel_tool_calls: True` to the streaming call as well

### Step 4: Verify Configuration Options

Check that these are already configurable (they should be based on earlier fixes):

**In config_flow.py:**

- ✅ `CONF_REASONING_LEVEL` - Already exists (lines 295-308)
- ✅ `CONF_VERBOSITY` - Already exists (lines 313-326)
- ✅ `CONF_CHAT_MODEL` - Already exists (lines 228-235)

**Verify these work with GPT-5 models:**

- "gpt-5" ✅
- "gpt-5-mini" ✅
- "gpt-5-nano" ✅
- "gpt-5-pro" ✅

All defined in `const.py` line 179: `GPT5_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro"]`

### Step 5: Add Text Format Parameter

According to the example code provided, we should also set:
"text": {
    "verbosity": "medium",
    "format": {"type": "text"}  # ✅ ADD THIS
}

### Step 6: Test Changes

Before committing:

1. Verify no syntax errors
2. Check linter
3. Verify all imports work

### Step 7: Commit and Push to Git

Following the user's memory about automatic commits:

- Stage all changes
- Commit with descriptive message
- Push to current branch (main)
- Delete any swap files automatically

## Files to Modify

1. **manifest.json** - Update openai version requirement
2. **requirements.txt** - Update openai version
3. **setup.py** - Update openai version
4. **init.py** - Add `parallel_tool_calls` and `stream` parameters, add text format
5. **Git operations** - Commit and push changes

## Example Final Response API Call

```python
{
    "model": "gpt-5",
    "input": messages,
    "max_output_tokens": 200,
    "parallel_tool_calls": True,
    "stream": True,
    "store": True,
    "reasoning": {
        "effort": "medium"  # Configurable in HA
    },
    "text": {
        "verbosity": "medium",  # Configurable in HA
        "format": {"type": "text"}
    },
    "tools": [
        # Function tools, MCP tools, web_search...
    ]
}
```

## Testing Checklist

- [ ] Library installs successfully
- [ ] parallel_tool_calls parameter is sent to API
- [ ] stream parameter is sent to API
- [ ] Reasoning effort can be changed in HA config
- [ ] Verbosity can be changed in HA config
- [ ] Model can be changed between GPT-5 variants
- [ ] No linter errors
- [ ] Git commit and push successful

### To-dos

- [ ] Add EXPOSED_ENTITIES_PROMPT_MAX constant to const.py
- [ ] Remove temperature and top_p from Responses API request in __init__.py
- [ ] Add allowed_tools and require_approval support to MCP tools configuration
- [ ] Update config_flow.py to clarify temperature/top_p are not used with Responses API
- [ ] Update README.md to reflect correct Responses API parameters