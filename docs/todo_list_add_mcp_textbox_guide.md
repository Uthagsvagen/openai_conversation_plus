# stöd för ytterligare textbox för MCP-servrar i OpenAI Conversation Plus

Denna guide visar hur du utökar integrationen med en ny options-textbox för att konfigurera MCP-servrar. Dessa skickas vidare till OpenAI Responses API som `type: mcp`-tools, vilket gör att modellen kan anropa flera MCP-servrar direkt.

Läs denna sida för hur openAI hanterar MCP
https://platform.openai.com/docs/guides/tools-connectors-mcp

---

## steg 1 – const.py
```python
CONF_MCP_SERVERS = "mcp_servers"
DEFAULT_MCP_SERVERS = ""
```

---

## steg 2 – options UI
Lägg till ett nytt `TextAreaSelector` i din options-flow:

```python
from homeassistant.helpers import selector
from .const import CONF_MCP_SERVERS, DEFAULT_MCP_SERVERS

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_FUNCTIONS, default=entry.options.get(CONF_FUNCTIONS, DEFAULT_CONF_FUNCTIONS_YAML)): selector.TextAreaSelector(),
        vol.Optional(CONF_MCP_SERVERS, default=entry.options.get(CONF_MCP_SERVERS, DEFAULT_MCP_SERVERS)): selector.TextAreaSelector(),
    }
)
```

I `async_step_init`:
```python
async def async_step_init(self, user_input=None):
    if user_input is not None:
        return self.async_create_entry(title="", data=user_input)
    data = {
        CONF_FUNCTIONS: self.config_entry.options.get(CONF_FUNCTIONS, DEFAULT_CONF_FUNCTIONS_YAML),
        CONF_MCP_SERVERS: self.config_entry.options.get(CONF_MCP_SERVERS, DEFAULT_MCP_SERVERS),
    }
    return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)
```

---

## steg 3 – parser för MCP-textbox
Skapa en hjälpfunktion för att normalisera YAML och bygga verktyg:

```python
import yaml
from .const import CONF_MCP_SERVERS

def _normalize_mcp_items(data):
    if isinstance(data, dict) and "mcpServers" in data:
        items = []
        for label, cfg in data["mcpServers"].items():
            url = None
            key = None
            if isinstance(cfg, dict):
                url = cfg.get("server_url") or cfg.get("url")
                if not url and isinstance(cfg.get("args"), list) and cfg["args"]:
                    url = cfg["args"][0]
                key = cfg.get("server_api_key") or cfg.get("api_key")
            items.append({"server_label": label, "server_url": url, "server_api_key": key})
        return items
    if isinstance(data, list):
        return [
            {
                "server_label": it.get("server_label") or it.get("label"),
                "server_url": it.get("server_url") or it.get("url"),
                "server_api_key": it.get("server_api_key") or it.get("api_key"),
            }
            for it in data if isinstance(it, dict)
        ]
    return []

def build_mcp_tools_from_options(options):
    raw = options.get(CONF_MCP_SERVERS) or ""
    try:
        data = yaml.safe_load(raw) if raw.strip() else None
    except Exception:
        return []
    items = _normalize_mcp_items(data) if data else []
    tools = []
    for it in items:
        if it.get("server_label") and it.get("server_url"):
            tool = {"type": "mcp", "server_label": it["server_label"], "server_url": it["server_url"]}
            if it.get("server_api_key"):
                tool["server_api_key"] = it["server_api_key"]
            tools.append(tool)
    return tools
```

---

## steg 4 – inkludera i query(...)
```python
mcp_tools = build_mcp_tools_from_options(self.entry.options)
api_tools.extend(mcp_tools)
validated_tools = []
for tool in api_tools:
    t = tool.get("type")
    if t == "function" and tool.get("name"):
        validated_tools.append(tool)
    elif t == "web_search":
        validated_tools.append(tool)
    elif t == "mcp" and tool.get("server_label") and tool.get("server_url"):
        validated_tools.append(tool)
if validated_tools:
    response_kwargs["tools"] = validated_tools
    response_kwargs["tool_choice"] = function_call
```

---

## steg 5 – exempel på YAML i textbox

enkel lista:
```yaml
- server_label: "Home Assistant"
  server_url: "https://ha.uthagsvagen.com/mcp_server/sse"
  server_api_key: "xxxxxx"
- server_label: "Sheets"
  server_url: "https://sheets.example.com/sse"
```

kompatibel med `mcpServers`-format:
```yaml
mcpServers:
  Home Assistant:
    command: mcp-proxy
    args:
      - https://ha.uthagsvagen.com/mcp_server/sse
    env:
      API_ACCESS_TOKEN: xxxxxx
  Sheets:
    url: https://sheets.example.com/sse
    api_key: yyyyyy
```

---

## steg 6 – validering (frivilligt)
Kör `build_mcp_tools_from_options` i `async_step_init` och returnera `errors={"base": "invalid_mcp_yaml"}` om användaren klistrar in felaktig YAML.
