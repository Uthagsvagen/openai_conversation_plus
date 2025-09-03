# MCP (Model Context Protocol) Server Examples

This directory contains examples and documentation for configuring MCP servers with OpenAI Conversation Plus.

## What is MCP?

MCP (Model Context Protocol) is OpenAI's standard protocol for connecting AI models to external tools and services. It enables your Home Assistant AI agent to:
- Access external databases and APIs
- Control remote systems and services
- Query real-time information from various sources
- Integrate with third-party platforms

## Configuration

MCP servers are configured in the integration's options page through a YAML text field. The integration supports two configuration formats for maximum flexibility.

### Format 1: Simple List

The simplest way to configure MCP servers:

```yaml
- server_label: "Home Assistant Remote"
  server_url: "https://remote-ha.example.com/mcp_server/sse"
  server_api_key: "your-api-key-here"

- server_label: "Google Sheets"
  server_url: "https://sheets-mcp.example.com/sse"
  server_api_key: "sheets-api-key"

- server_label: "GitHub"
  server_url: "https://github-mcp.example.com/sse"
  server_api_key: "github-token"
```

### Format 2: mcpServers Compatible

Compatible with the standard mcpServers configuration format:

```yaml
mcpServers:
  Home Assistant Remote:
    command: mcp-proxy
    args:
      - https://remote-ha.example.com/mcp_server/sse
    env:
      API_ACCESS_TOKEN: your-api-key-here
  
  Google Sheets:
    url: https://sheets-mcp.example.com/sse
    api_key: sheets-api-key
  
  GitHub:
    url: https://github-mcp.example.com/sse
    api_key: github-token
```

## Real-World Examples

### Example 1: Home Automation Hub

Connect multiple Home Assistant instances or smart home platforms:

```yaml
- server_label: "Main House"
  server_url: "https://main.home.local/mcp_server/sse"
  server_api_key: "main-house-key"

- server_label: "Guest House"
  server_url: "https://guest.home.local/mcp_server/sse"
  server_api_key: "guest-house-key"

- server_label: "SmartThings"
  server_url: "https://smartthings-mcp.local/sse"
  server_api_key: "smartthings-key"
```

### Example 2: Business Tools Integration

Connect productivity and business tools:

```yaml
mcpServers:
  Slack:
    url: https://slack-mcp.company.com/sse
    api_key: xoxb-slack-bot-token
  
  Jira:
    url: https://jira-mcp.company.com/sse
    api_key: jira-api-token
    
  Calendar:
    url: https://calendar-mcp.company.com/sse
    api_key: calendar-access-token
```

### Example 3: Data Sources

Connect to various data sources and databases:

```yaml
- server_label: "Weather Station"
  server_url: "wss://weather.local/mcp/stream"
  server_api_key: "weather-api-key"

- server_label: "Energy Monitor"
  server_url: "https://energy.local/mcp_server/sse"
  server_api_key: "energy-key"

- server_label: "Stock Market"
  server_url: "https://stocks-mcp.service.com/sse"
  server_api_key: "market-data-key"
```

## How It Works

When configured, MCP servers are passed to the OpenAI Responses API as tools of type `"mcp"`. The AI model can then:

1. **Discover capabilities** - Query what functions each MCP server provides
2. **Execute operations** - Call specific functions on the MCP servers
3. **Retrieve data** - Get real-time information from connected services
4. **Perform actions** - Control and automate external systems

## Security Considerations

- **API Keys**: Store API keys securely and never commit them to version control
- **URLs**: Use HTTPS/WSS for encrypted connections whenever possible
- **Access Control**: Ensure MCP servers have appropriate authentication and authorization
- **Network**: Consider using VPNs or private networks for sensitive services

## Troubleshooting

### Common Issues

1. **Server not responding**
   - Verify the server URL is correct and accessible
   - Check if API key is valid and has proper permissions
   - Ensure the server supports MCP protocol

2. **Functions not available**
   - Confirm the MCP server is properly configured
   - Check Home Assistant logs for connection errors
   - Verify the model has tools enabled in options

3. **Authentication failures**
   - Double-check API keys are entered correctly
   - Ensure keys have not expired
   - Verify server accepts the authentication method

### Debug Logging

Enable debug logging for the integration to see MCP-related messages:

```yaml
logger:
  default: info
  logs:
    custom_components.openai_conversation_plus: debug
```

## Advanced Configuration

### Environment-Specific Settings

Use Home Assistant secrets for sensitive data:

```yaml
# In configuration YAML
- server_label: "Production DB"
  server_url: !secret mcp_prod_url
  server_api_key: !secret mcp_prod_key
```

### Dynamic Server Discovery

Some MCP servers support dynamic discovery. Configure the base server:

```yaml
- server_label: "Service Discovery"
  server_url: "https://mcp-discovery.local/sse"
  server_api_key: "discovery-key"
```

The AI can then query this server to discover and connect to other available services.

## Contributing

If you've created an MCP server integration or have examples to share:
1. Fork this repository
2. Add your example to this directory
3. Submit a pull request

## Resources

- [OpenAI MCP Documentation](https://platform.openai.com/docs/guides/tools-connectors-mcp)
- [Home Assistant Integration Development](https://developers.home-assistant.io/)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)

## Support

For issues or questions about MCP configuration:
- Check the [main README](../../README.md)
- Open an issue on [GitHub](https://github.com/Uthagsvagen/openai_conversation_plus)
- Visit the Home Assistant Community forums
