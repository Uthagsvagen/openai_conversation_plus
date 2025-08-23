# Quick Fix Instructions

## To apply the fixes for "Unexpected error during intent recognition":

1. **Update the integration**:
   ```bash
   cd /config/custom_components/extended_openai_conversation
   git pull
   ```

2. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Or use: `ha core restart`

3. **Clear browser cache**:
   - Safari: Cmd+Shift+R
   - Chrome/Firefox: Ctrl+Shift+R

4. **Test the chat**:
   - Open Assist/Chat
   - Try a simple message like "Hello"

## If still not working:

1. **Enable debug logging** in configuration.yaml:
   ```yaml
   logger:
     logs:
       custom_components.extended_openai_conversation: debug
   ```

2. **Check the logs**:
   - Settings → System → Logs
   - Look for specific error messages

3. **Try disabling advanced features**:
   - Go to the integration settings
   - Disable "Use Response API"
   - Disable "Enable Web Search"
   - Save and restart

The main fixes applied:
- ✅ Fixed model_dump() compatibility issue
- ✅ Added comprehensive error handling
- ✅ Added null safety checks
- ✅ Improved debug logging

Your custom functions are preserved and will continue to work!
