# Troubleshooting Guide - OpenAI Conversation Plus

## Common Issues and Solutions

### "Unexpected error during intent recognition"

This error typically occurs when the integration encounters issues processing the conversation. Here are the fixes that have been implemented:

#### Fixed Issues:
1. **model_dump() compatibility** - Replaced with manual dictionary conversion
2. **Missing exception handling** - Added comprehensive error catching
3. **None value errors** - Added null checks and attribute guards
4. **Safari compatibility** - Frontend websocket issues

#### If the error persists:

1. **Check Home Assistant logs**:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.openai_conversation_plus: debug
   ```

2. **Restart Home Assistant**:
   - After updating the integration files
   - Clear browser cache (especially in Safari)

3. **Verify API Key**:
   - Ensure your OpenAI API key is valid
   - Check if you have API credits/quota

4. **Test with different browser**:
   - Safari has known compatibility issues
   - Try Chrome, Firefox, or Edge

5. **Check configuration**:
   - Ensure all required fields are filled
   - Try disabling advanced features temporarily

### Safari WebSocket Errors

If you see `ReferenceError: Cannot access uninitialized variable` in Safari:

1. Copy `safari-fix.js` to your Home Assistant `www/` folder
2. Add to `configuration.yaml`:
   ```yaml
   frontend:
     extra_module_url:
       - /local/safari-fix.js
   ```
3. Restart Home Assistant and clear Safari cache

### Integration Not Loading

1. Check `manifest.json` is valid JSON
2. Ensure all dependencies are installed
3. Check Home Assistant version compatibility (requires 2024.1.0+)

### No Response from AI

1. Check OpenAI service status: https://status.openai.com/
2. Verify API key permissions
3. Try a simpler model (gpt-4o-mini)
4. Disable Response API temporarily

## Debug Mode

To enable detailed logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.openai_conversation_plus: debug
    homeassistant.components.conversation: debug
    openai: debug
```

## Getting Help

1. Check the logs first - they usually contain the specific error
2. Create an issue at: https://github.com/aselling/openai_conversation_plus/issues
3. Include:
   - Home Assistant version
   - Browser and version
   - Error messages from logs
   - Configuration (without API key)
