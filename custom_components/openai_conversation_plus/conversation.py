from __future__ import annotations

from typing import Any, Literal
import json
import logging

from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import (
    async_should_expose,
)
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import entity_registry as er, template

from openai import AsyncOpenAI
from openai._exceptions import OpenAIError

from .const import (
    DOMAIN,
    CONF_CHAT_MODEL,
    DEFAULT_CHAT_MODEL,
    CONF_STORE_CONVERSATIONS,
    DEFAULT_STORE_CONVERSATIONS,
    INTEGRATION_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([OpenAIConversationEntity(entry)])


class OpenAIConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    # Enable streaming per HA pattern; we'll stream deltas when possible
    _attr_supports_streaming = True

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        opts = self.entry.options
        client: AsyncOpenAI = self.entry.runtime_data  # type: ignore[attr-defined]

        # Provide LLM context and tools from HA to the model
        try:
            # Render the prompt template without entities
            rendered_prompt = template.Template(
                (opts.get("prompt") or ""),
                self.hass,
            ).async_render(
                {
                    "ha_name": self.hass.config.location_name or "Home",
                    "current_device_id": getattr(user_input, "device_id", None),
                },
                parse_result=False,
                strict=False,
            )
            
            # For new conversations (empty chat log), append entities directly
            # This avoids template size limits and ensures entities are always included
            is_new_conversation = len(chat_log.content) == 0
            _LOGGER.info("[v%s] Conversation state: new=%s, chat_log_length=%d", 
                        INTEGRATION_VERSION, is_new_conversation, len(chat_log.content))
            
            if is_new_conversation:
                exposed = self._get_exposed_entities()
                _LOGGER.info("[v%s] Fetched %d exposed entities for new conversation", 
                            INTEGRATION_VERSION, len(exposed) if exposed else 0)
                
                if exposed:
                    # Limit entities to avoid token limits
                    from .const import EXPOSED_ENTITIES_PROMPT_MAX
                    limited_exposed = exposed[:EXPOSED_ENTITIES_PROMPT_MAX]
                    entities_json = json.dumps(limited_exposed, ensure_ascii=False)
                    rendered_prompt = f"{rendered_prompt}\n\nAvailable entities:\n{entities_json}"
                    _LOGGER.info(
                        "[v%s] Appended %d entities to conversation system prompt (limited from %d)",
                        INTEGRATION_VERSION,
                        len(limited_exposed),
                        len(exposed)
                    )
                else:
                    _LOGGER.warning("[v%s] No exposed entities found for conversation", INTEGRATION_VERSION)
            
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                opts.get("llm_hass_api"),
                rendered_prompt,
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        # Convert HA LLM API tools to Responses API tools
        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = []
            for t in chat_log.llm_api.tools:
                # Use nested structure (Chat Completions style) which Responses API also accepts
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": getattr(t, "description", ""),
                            "parameters": getattr(t, "parameters", {}),
                        }
                    }
                )
        
        # CRITICAL: Add custom functions from integration options
        # This is where user-defined functions like execute_services are loaded!
        from . import get_functions_from_options
        user_functions = get_functions_from_options(opts)
        
        _LOGGER.info(
            "[v%s] Loading user-defined functions from options: %d found",
            INTEGRATION_VERSION,
            len(user_functions) if user_functions else 0
        )
        
        if user_functions:
            if tools is None:
                tools = []
            for func_setting in user_functions:
                func_spec = func_setting.get("spec", {})
                if func_spec and "name" in func_spec:
                    tool = {
                        "type": "function",
                        "function": {
                            "name": func_spec.get("name"),
                            "description": func_spec.get("description", ""),
                            "parameters": func_spec.get("parameters", {"type": "object", "properties": {}})
                        }
                    }
                    tools.append(tool)
                    _LOGGER.info(
                        "[v%s]   - Added function: %s",
                        INTEGRATION_VERSION,
                        func_spec.get("name")
                    )
        
        # Add MCP servers as tools
        from . import build_mcp_tools_from_options
        mcp_tools = build_mcp_tools_from_options(opts)
        if mcp_tools:
            if tools is None:
                tools = []
            tools.extend(mcp_tools)
            _LOGGER.info(
                "[v%s] Added %d MCP tools to conversation",
                INTEGRATION_VERSION,
                len(mcp_tools)
            )

        # Build Responses API input from chat log
        msgs: list[dict[str, Any]] = []
        for c in chat_log.content:
            is_user = getattr(c, "is_user", False)
            role = "user" if is_user else "assistant"
            text = getattr(c, "content", "") or ""
            # Use input_text for user messages, output_text for assistant messages
            content_type = "input_text" if is_user else "output_text"
            msgs.append(
                {
                    "type": "message",
                    "role": role,
                    "content": [
                        {
                            "type": content_type,
                            "text": text,
                        }
                    ],
                }
            )

        model = opts.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        max_tokens = opts.get("max_tokens", 150)
        
        kwargs: dict[str, Any] = {
            "model": model,
            "input": msgs,
            "max_output_tokens": max_tokens,
            "parallel_tool_calls": True,
            "store": opts.get(CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS),
        }
        
        # Add reasoning and verbosity for GPT-5 models
        from .const import GPT5_MODELS, VERBOSITY_COMPAT_MAP
        if model in GPT5_MODELS:
            reasoning_level = opts.get("reasoning_level", "medium")
            verbosity = opts.get("verbosity", "medium")
            # Map legacy verbosity values
            mapped_verbosity = VERBOSITY_COMPAT_MAP.get(verbosity, verbosity)
            
            kwargs["reasoning"] = {"effort": reasoning_level}
            kwargs["text"] = {
                "verbosity": mapped_verbosity,
                "format": {"type": "text"}
            }
            _LOGGER.info(
                "[v%s] GPT-5 settings: reasoning=%s, verbosity=%s",
                INTEGRATION_VERSION,
                reasoning_level,
                mapped_verbosity
            )
        
        if tools:
            # Sanitize tool definitions for the Responses API (strip unsupported fields like server_api_key)
            try:
                from . import sanitize_tools_for_responses
                tools = sanitize_tools_for_responses(tools)
            except Exception:  # noqa: BLE001
                # If sanitize is not available for any reason, fall back to original tools
                pass
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
            # Streaming IS supported with tools according to official docs!
            from .const import CONF_STREAM_ENABLED, DEFAULT_STREAM_ENABLED
            stream_enabled = opts.get(CONF_STREAM_ENABLED, DEFAULT_STREAM_ENABLED)
            kwargs["stream"] = bool(stream_enabled)
            _LOGGER.info(
                "[v%s] Sending %d tools to OpenAI (stream=%s, tool_choice=%s)",
                INTEGRATION_VERSION,
                len(tools),
                kwargs.get("stream"),
                kwargs.get("tool_choice")
            )
        else:
            from .const import CONF_STREAM_ENABLED, DEFAULT_STREAM_ENABLED
            kwargs["stream"] = opts.get(CONF_STREAM_ENABLED, DEFAULT_STREAM_ENABLED)
            _LOGGER.warning(
                "[v%s] No tools configured - model cannot control devices!",
                INTEGRATION_VERSION
            )

        # Enhanced final logging before sending to OpenAI
        _LOGGER.info(
            "[v%s] Final kwargs summary - model=%s, stream=%s, parallel_tool_calls=%s, tools=%d, tool_choice=%s",
            INTEGRATION_VERSION,
            kwargs.get("model"),
            kwargs.get("stream"),
            kwargs.get("parallel_tool_calls"),
            len(kwargs.get("tools", [])),
            kwargs.get("tool_choice", "none")
        )
        _LOGGER.debug("[v%s] Complete kwargs being sent to Responses API: %s", INTEGRATION_VERSION, json.dumps(kwargs, default=str))
        
        # Use streaming only if enabled
        use_streaming = kwargs.get("stream", True)
        
        try:
            # Create a delta stream in the chat log
            stream_obj = getattr(chat_log, "async_add_delta_content_stream", None)
            if use_streaming and callable(stream_obj):
                delta_stream = chat_log.async_add_delta_content_stream(
                    AssistantContent(agent_id=user_input.agent_id, content="")
                )
                try:
                    # OpenAI Responses streaming
                    stream_ctx = getattr(client.responses, "stream", None)
                    if stream_ctx is None:
                        raise RuntimeError("Responses streaming not available")

                    async with client.responses.stream(**kwargs) as resp_stream:
                        pending_tool_calls: list[dict[str, Any]] = []
                        async for event in resp_stream:
                            etype = getattr(event, "type", "")
                            _LOGGER.debug("[v%s] Streaming event: %s", INTEGRATION_VERSION, etype)
                            
                            # Stream text deltas - Use correct event names per official docs
                            if etype == "response.output_text.delta":
                                delta_text = getattr(event, "delta", None)
                                if delta_text:
                                    push = getattr(delta_stream, "async_push_delta", None)
                                    if callable(push):
                                        await delta_stream.async_push_delta(delta_text)
                            
                            # Function call events per official docs
                            elif etype == "response.function_call.arguments.delta":
                                fn_args = getattr(event, "delta", None)
                                if fn_args and pending_tool_calls:
                                    pending_tool_calls[-1]["arguments"] += fn_args
                                    
                            elif etype == "response.function_call.arguments.done":
                                # Function call completed - execute it
                                fn = getattr(event, "function_call", None)
                                if fn:
                                    func_name = getattr(fn, "name", None)
                                    arguments = getattr(fn, "arguments", "{}")
                                    
                                    if func_name:
                                        _LOGGER.info("[v%s] Streaming function call: %s", INTEGRATION_VERSION, func_name)
                                        try:
                                            args = json.loads(arguments)
                                        except Exception:
                                            args = {}
                                        
                                        from . import get_functions_from_options
                                        functions = get_functions_from_options(opts)
                                        fn_def = next((f for f in functions if f["spec"]["name"] == func_name), None)
                                        if fn_def:
                                            from .helpers import get_function_executor
                                            executor = get_function_executor(fn_def["function"]["type"])
                                            result = await executor.execute(
                                                self.hass,
                                                fn_def["function"],
                                                args,
                                                user_input,
                                                self._get_exposed_entities(),
                                            )
                                            _LOGGER.info("[v%s] Executed streaming function call: %s", INTEGRATION_VERSION, func_name)
                                            
                            # Also handle legacy event names as fallback (for compatibility)
                            elif etype.endswith("output_text.delta"):
                                delta = getattr(event, "delta", None)
                                if delta:
                                    push = getattr(delta_stream, "async_push_delta", None)
                                    if callable(push):
                                        await delta_stream.async_push_delta(delta)
                            elif etype.endswith("function_call.created") or "tool_call" in etype:
                                # Legacy handling - keep for backward compatibility
                                fn = getattr(event, "function", None)
                                if fn and getattr(fn, "name", None):
                                    pending_tool_calls.append({
                                        "id": getattr(event, "id", None),
                                        "name": fn.name,
                                        "arguments": getattr(fn, "arguments", "{}"),
                                    })
                        # Final response
                        final = await resp_stream.get_final_response()
                        # Parse streaming final response using same logic as non-streaming
                        out = ""
                        try:
                            out = getattr(final, "output_text", None)
                            if not out:
                                # Parse manual structure: response.output[].content[].text
                                if hasattr(final, "output") and final.output:
                                    for output_item in final.output:
                                        if getattr(output_item, "type", "") == "message":
                                            content_items = getattr(output_item, "content", [])
                                            for content_item in content_items:
                                                if getattr(content_item, "type", "") == "output_text":
                                                    text = getattr(content_item, "text", "")
                                                    if text:
                                                        out += text + "\n"
                            out = out.strip() if out else ""
                        except Exception as e:
                            _LOGGER.error("[v%s] Error parsing streaming final response: %s", INTEGRATION_VERSION, e)
                            out = ""
                finally:
                    # Ensure stream is closed
                    close = getattr(delta_stream, "async_end", None)
                    if callable(close):
                        await delta_stream.async_end()
            else:
                raise RuntimeError("ChatLog delta stream not available")
        except Exception:
            # Non-streaming fallback with defensive retries for tool/schema issues
            try:
                final = await client.responses.create(**kwargs)
            except TypeError:
                # Remove potentially unsupported fields just in case
                kwargs.pop("response_format", None)
                kwargs.pop("text", None)
                kwargs.pop("reasoning", None)
                final = await client.responses.create(**kwargs)
            except OpenAIError as e:
                if "tools" in str(e):
                    # Retry without tools if the provider rejects tool schema
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    final = await client.responses.create(**kwargs)
                else:
                    raise
            
            # Parse response according to official Responses API structure
            out = ""
            try:
                # Try SDK convenience property first
                out = getattr(final, "output_text", None)
                if not out:
                    # Parse manual structure: response.output[].content[].text
                    if hasattr(final, "output") and final.output:
                        for output_item in final.output:
                            if getattr(output_item, "type", "") == "message":
                                content_items = getattr(output_item, "content", [])
                                for content_item in content_items:
                                    if getattr(content_item, "type", "") == "output_text":
                                        text = getattr(content_item, "text", "")
                                        if text:
                                            out += text + "\n"
                out = out.strip() if out else ""
                _LOGGER.debug("[v%s] Parsed response text: %s", INTEGRATION_VERSION, out[:100] + "..." if len(out) > 100 else out)
            except Exception as e:
                _LOGGER.error("[v%s] Error parsing response structure: %s", INTEGRATION_VERSION, e)
                out = ""

        # Check if the response contains tool calls according to Responses API structure
        # Tool calls are found in the response.output[].content[] items
        tool_calls = []
        try:
            # First try SDK convenience property
            tool_calls = getattr(final, "tool_calls", None) or []
            
            # If no tool calls via SDK property, parse from output structure
            if not tool_calls and hasattr(final, "output") and final.output:
                for output_item in final.output:
                    if getattr(output_item, "type", "") == "message":
                        # Check if this message has tool calls
                        if hasattr(output_item, "tool_calls"):
                            tool_calls.extend(output_item.tool_calls)
        except Exception as e:
            _LOGGER.error("[v%s] Error parsing tool calls from response: %s", INTEGRATION_VERSION, e)
            tool_calls = []
            
        if tool_calls:
            _LOGGER.info("[v%s] Processing %d tool calls from Responses API", INTEGRATION_VERSION, len(tool_calls))
            results = []
            for tool_call in tool_calls:
                try:
                    if hasattr(tool_call, 'function'):
                        func_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        _LOGGER.debug("[v%s] Executing tool call: %s with args: %s", INTEGRATION_VERSION, func_name, arguments)
                        
                        # Find the matching function from configured tools
                        from . import get_functions_from_options
                        functions = get_functions_from_options(opts)
                        matching_func = next((f for f in functions if f["spec"]["name"] == func_name), None)
                        
                        if matching_func:
                            from .helpers import get_function_executor
                            executor = get_function_executor(matching_func["function"]["type"])
                            result = await executor.execute(
                                self.hass,
                                matching_func["function"],
                                arguments,
                                user_input,
                                self._get_exposed_entities(),
                            )
                            results.append(f"Executed {func_name}: {result}")
                        else:
                            _LOGGER.warning("[v%s] No matching function found for: %s", INTEGRATION_VERSION, func_name)
                            results.append(f"Unknown function: {func_name}")
                except Exception as e:
                    _LOGGER.error("[v%s] Failed to execute tool call: %s", INTEGRATION_VERSION, e)
                    results.append(f"Error executing {getattr(tool_call, 'function', {}).get('name', 'unknown')}: {e}")
            
            if results:
                out = ". ".join(results) if len(results) > 1 else results[0]
        
        # Fallback: If the model returned JSON in output_text, try to parse and execute
        elif out and (out.strip().startswith("[") or out.strip().startswith("{")):
            try:
                payload = json.loads(out)
                _LOGGER.info("[v%s] Detected JSON in output_text, attempting to parse as tool call", INTEGRATION_VERSION)
                
                # Handle array format: [{"domain":"light","service":"turn_on",...}]
                if isinstance(payload, list):
                    _LOGGER.debug("[v%s] Processing array format with %d items", INTEGRATION_VERSION, len(payload))
                    results = []
                    for item in payload:
                        if isinstance(item, dict) and "domain" in item and "service" in item:
                            # This is a direct service call format
                            from .helpers import get_function_executor
                            executor = get_function_executor("native")
                            fn_config = {"type": "native", "name": "execute_service"}
                            
                            # Normalize the service call format
                            service_call = {
                                "list": [{
                                    "domain": item.get("domain"),
                                    "service": item.get("service"),
                                    "target": item.get("target", {}),
                                    "service_data": item.get("data") or item.get("service_data", {})
                                }]
                            }
                            
                            try:
                                result = await executor.execute(
                                    self.hass,
                                    fn_config,
                                    service_call,
                                    user_input,
                                    self._get_exposed_entities(),
                                )
                                results.append(f"Executed {item['domain']}.{item['service']}")
                                _LOGGER.info("[v%s] Successfully executed service: %s.%s", INTEGRATION_VERSION, item['domain'], item['service'])
                            except Exception as e:
                                _LOGGER.error("[v%s] Failed to execute service: %s", INTEGRATION_VERSION, e)
                                results.append(f"Error: {e}")
                    
                    out = "Utfört." if results else out
                
                # Handle object format for backward compatibility
                elif isinstance(payload, dict):
                    # Check for both "actions" and "calls" keys (different formats from OpenAI)
                    actions_list = payload.get("actions") or payload.get("calls", [])
                    if payload.get("type") == "execute_services" and isinstance(actions_list, list):
                        _LOGGER.info("[v%s] Processing execute_services format with %d actions", INTEGRATION_VERSION, len(actions_list))
                        norm = {"execute_services": {"list": []}}
                        for c in actions_list:
                            item = {
                                "domain": c.get("domain"),
                                "service": c.get("service"),
                            }
                            tgt = c.get("target") or {}
                            if "entity_id" in tgt:
                                item["target"] = {"entity_id": tgt["entity_id"]}
                            elif "area_name" in tgt:
                                item["target"] = {"area_name": tgt["area_name"]}
                            elif "area_id" in tgt:
                                # Handle both single area_id and list of area_ids
                                area_ids = tgt["area_id"]
                                if isinstance(area_ids, list):
                                    item["target"] = {"area_name": area_ids[0] if area_ids else ""}
                                else:
                                    item["target"] = {"area_name": area_ids}
                            elif "area" in tgt:
                                item["target"] = {"area_name": tgt["area"]}
                            elif "device_id" in tgt:
                                item["target"] = {"device_id": tgt["device_id"]}
                            data = c.get("service_data") or c.get("data") or {}
                            if data:
                                item["service_data"] = data
                            norm["execute_services"]["list"].append(item)
                        
                        from .helpers import get_function_executor
                        function_executor = get_function_executor("native")
                        fn_config = {"type": "native", "name": "execute_service"}
                        await function_executor.execute(
                            self.hass,
                            fn_config,
                            norm["execute_services"],
                            user_input,
                            self._get_exposed_entities(),
                        )
                        out = "Utfört."
                        _LOGGER.info("[v%s] Executed services from object format", INTEGRATION_VERSION)
            except json.JSONDecodeError as e:
                _LOGGER.debug("[v%s] Failed to parse JSON from output_text: %s", INTEGRATION_VERSION, e)
                # Keep original output if not JSON
                pass
            except Exception as e:
                _LOGGER.error("[v%s] Error processing JSON tool call: %s", INTEGRATION_VERSION, e)
                # Keep original output on error
                pass

        # Append the assistant message (final text) and return
        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=out)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    def _get_exposed_entities(self) -> list[dict[str, Any]]:
        try:
            entry_id = getattr(self.entry, "entry_id", None)
            all_states = self.hass.states.async_all()
            states = [
                s for s in all_states if async_should_expose(self.hass, entry_id, s.entity_id)
            ]
            if not states:
                _LOGGER.info(
                    "[v%s] No entities exposed for conversation agent; falling back to all (%d)",
                    INTEGRATION_VERSION,
                    len(all_states),
                )
                states = all_states
            reg = er.async_get(self.hass)
            out: list[dict[str, Any]] = []
            for s in states:
                try:
                    entity = reg.async_get(s.entity_id)
                    aliases = list(getattr(entity, "aliases", []) or []) if entity else []
                    cur = self.hass.states.get(s.entity_id)
                    out.append(
                        {
                            "entity_id": s.entity_id,
                            "name": getattr(s, "name", s.entity_id) or s.entity_id,
                            "state": (cur.state if cur else "unavailable"),
                            "aliases": aliases,
                        }
                    )
                except Exception:  # noqa: BLE001
                    continue
            _LOGGER.info(
                "[v%s] Exposed entities prepared for conversation: %d / %d",
                INTEGRATION_VERSION,
                len(states),
                len(all_states),
            )
            return out
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("[v%s] Failed to build exposed entities for conversation: %s", INTEGRATION_VERSION, err)
            return []


