from __future__ import annotations

from typing import Any, Literal
import json
import logging
import os
from datetime import datetime
from pathlib import Path

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


def _save_api_log(hass: HomeAssistant, log_type: str, data: dict) -> None:
    """Save API request/response to log file for debugging."""
    try:
        # Create logs directory in Home Assistant config directory
        logs_dir = Path(hass.config.path("custom_components", "openai_conversation_plus", "logs"))
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{log_type}.json"
        filepath = logs_dir / filename
        
        # Save the data
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        _LOGGER.info("[v%s] Saved %s log to: %s", INTEGRATION_VERSION, log_type, filepath)
    except Exception as e:
        _LOGGER.error("[v%s] Failed to save API log: %s", INTEGRATION_VERSION, e)


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
                # Use flat structure required by Responses API
                tools.append(
                    {
                        "type": "function",
                        "name": t.name,
                        "description": getattr(t, "description", ""),
                        "parameters": getattr(t, "parameters", {}),
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
                    # Use flat structure required by Responses API
                    tool = {
                        "type": "function",
                        "name": func_spec.get("name"),
                        "description": func_spec.get("description", ""),
                        "parameters": func_spec.get("parameters", {"type": "object", "properties": {}})
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
        # Use the flat message format per Responses API spec
        msgs: list[dict[str, Any]] = []
        
        for idx, c in enumerate(chat_log.content):
            role = getattr(c, "role", None)
            is_user = getattr(c, "is_user", False)
            text = getattr(c, "content", "") or ""
            
            _LOGGER.debug("[v%s] Chat log item %d: role=%s, is_user=%s, text_len=%d", 
                         INTEGRATION_VERSION, idx, role, is_user, len(text))
            
            # Determine correct role for Responses API
            # First message is typically system prompt
            if idx == 0 and role in ("system", "developer", None) and not is_user:
                msg_role = "system"
                _LOGGER.debug("[v%s] First message treated as system", INTEGRATION_VERSION)
            elif is_user or role == "user":
                msg_role = "user"
                _LOGGER.debug("[v%s] Message is user", INTEGRATION_VERSION)
            elif idx == len(chat_log.content) - 1 and not role:
                # Last message without explicit role defaults to user
                msg_role = "user"
                _LOGGER.debug("[v%s] Last message without role treated as user", INTEGRATION_VERSION)
            else:
                msg_role = "assistant"
                _LOGGER.debug("[v%s] Message is assistant", INTEGRATION_VERSION)
            
            # Use output_text for all content per Responses API examples
            msgs.append(
                {
                    "type": "message",
                    "role": msg_role,
                    "content": [
                        {
                            "type": "output_text",
                            "text": text,
                        }
                    ],
                }
            )
            _LOGGER.debug("[v%s] Added message with role=%s", INTEGRATION_VERSION, msg_role)
            
        _LOGGER.info("[v%s] Built %d messages from chat log", INTEGRATION_VERSION, len(msgs))

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
        
        # Save API request to log file for debugging
        _save_api_log(self.hass, "request", {
            "timestamp": datetime.now().isoformat(),
            "kwargs": kwargs,
            "tools_details": kwargs.get("tools", []),
            "messages_count": len(msgs),
            "has_llm_api": chat_log.llm_api is not None,
        })
        
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
                        pending_tool_calls: dict[str, dict[str, Any]] = {}  # Track by item_id
                        
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
                            
                            # Tool call start event
                            elif etype == "response.output_item.added":
                                item = getattr(event, "item", None)
                                if item and getattr(item, "type", "") == "tool":
                                    item_id = getattr(item, "id", None)
                                    if item_id:
                                        pending_tool_calls[item_id] = {
                                            "id": item_id,
                                            "name": getattr(item, "name", None),
                                            "arguments": ""
                                        }
                                        _LOGGER.debug("[v%s] Tool call started: %s", INTEGRATION_VERSION, getattr(item, "name", "unknown"))
                            
                            # Function call arguments delta
                            elif etype == "response.function_call_arguments.delta":
                                item_id = getattr(event, "item_id", None)
                                delta = getattr(event, "delta", None)
                                if item_id in pending_tool_calls and delta:
                                    pending_tool_calls[item_id]["arguments"] += delta
                            
                            # Function call arguments completed
                            elif etype == "response.function_call_arguments.done":
                                item_id = getattr(event, "item_id", None)
                                arguments_str = getattr(event, "arguments", None)
                                
                                if item_id in pending_tool_calls:
                                    tool_call = pending_tool_calls[item_id]
                                    if arguments_str:
                                        tool_call["arguments"] = arguments_str
                                    
                                    tool_name = tool_call["name"]
                                    
                                    if tool_name:
                                        _LOGGER.info("[v%s] Executing streaming tool call: %s", INTEGRATION_VERSION, tool_name)
                                        
                                        try:
                                            args = json.loads(tool_call["arguments"])
                                        except json.JSONDecodeError:
                                            args = {}
                                        
                                        # Find and execute the tool
                                        from . import get_functions_from_options
                                        functions = get_functions_from_options(opts)
                                        fn_def = next((f for f in functions if f["spec"]["name"] == tool_name), None)
                                        
                                        if fn_def:
                                            try:
                                                from .helpers import get_function_executor
                                                executor = get_function_executor(fn_def["function"]["type"])
                                                result = await executor.execute(
                                                    self.hass,
                                                    fn_def["function"],
                                                    args,
                                                    user_input,
                                                    self._get_exposed_entities(),
                                                )
                                                _LOGGER.info("[v%s] Executed streaming tool: %s - result: %s", INTEGRATION_VERSION, tool_name, str(result)[:100])
                                            except Exception as e:
                                                _LOGGER.error("[v%s] Failed to execute streaming tool %s: %s", INTEGRATION_VERSION, tool_name, e)
                                        else:
                                            # Check if it's a Home Assistant LLM API tool
                                            if chat_log.llm_api:
                                                try:
                                                    from homeassistant.helpers import llm
                                                    tool_input = llm.ToolInput(
                                                        tool_name=tool_name,
                                                        tool_args=args,
                                                        platform=DOMAIN,
                                                        context=user_input.context,
                                                        user_prompt=user_input.text,
                                                        language=user_input.language,
                                                        assistant=conversation.DOMAIN,
                                                        device_id=user_input.device_id,
                                                    )
                                                    result = await chat_log.llm_api.async_call_tool(tool_input)
                                                    _LOGGER.info("[v%s] Executed streaming HA LLM API tool: %s", INTEGRATION_VERSION, tool_name)
                                                except Exception as e:
                                                    _LOGGER.error("[v%s] Failed to execute streaming HA LLM API tool %s: %s", INTEGRATION_VERSION, tool_name, e)
                                            else:
                                                _LOGGER.warning("[v%s] No matching tool found for streaming call: %s", INTEGRATION_VERSION, tool_name)
                        # Final response
                        final = await resp_stream.get_final_response()
                        
                        # Save streaming response to log file
                        _save_api_log(self.hass, "streaming_response", {
                            "timestamp": datetime.now().isoformat(),
                            "response": {
                                "id": getattr(final, "id", None),
                                "model": getattr(final, "model", None),
                        "output": [
                            {
                                "type": getattr(item, "type", None),
                                "id": getattr(item, "id", None),
                                "content": getattr(item, "content", None) if getattr(item, "type", "") == "message" else None,
                                "name": getattr(item, "name", None) if getattr(item, "type", "") == "tool" else None,
                                "arguments": getattr(item, "arguments", None) if getattr(item, "type", "") == "tool" else None,
                            }
                            for item in (final.output if hasattr(final, "output") else [])
                        ],
                                "usage": getattr(final, "usage", None),
                            },
                            "pending_tool_calls": pending_tool_calls,
                        })
                        
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
        except Exception as stream_error:
            _LOGGER.warning("[v%s] Streaming failed: %s, falling back to non-streaming", INTEGRATION_VERSION, stream_error)
            # Non-streaming fallback with function execution loop
            max_iterations = 10
            conversation_items = msgs.copy()
            
            for iteration in range(max_iterations):
                _LOGGER.debug("[v%s] Non-streaming iteration %d/%d", INTEGRATION_VERSION, iteration + 1, max_iterations)
                
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
                
                # Save non-streaming response to log file
                _save_api_log(self.hass, f"non_streaming_response_iter_{iteration + 1}", {
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration + 1,
                    "response": {
                        "id": getattr(final, "id", None),
                        "model": getattr(final, "model", None),
                        "output": [
                            {
                                "type": getattr(item, "type", None),
                                "id": getattr(item, "id", None),
                                "content": getattr(item, "content", None) if getattr(item, "type", "") == "message" else None,
                                "name": getattr(item, "name", None) if getattr(item, "type", "") == "tool" else None,
                                "arguments": getattr(item, "arguments", None) if getattr(item, "type", "") == "tool" else None,
                            }
                            for item in (final.output if hasattr(final, "output") else [])
                        ],
                        "usage": getattr(final, "usage", None),
                    },
                })
                
                # Extract tool calls from response.output
                tool_calls = []
                if hasattr(final, "output") and final.output:
                    for output_item in final.output:
                        if getattr(output_item, "type", "") == "tool":
                            tool_calls.append(output_item)
                
                if not tool_calls:
                    # No more tool calls, we're done
                    _LOGGER.debug("[v%s] No tool calls in iteration %d, finishing", INTEGRATION_VERSION, iteration + 1)
                    break
                
                # Execute all tool calls and collect outputs
                _LOGGER.info("[v%s] Executing %d tool calls in iteration %d", INTEGRATION_VERSION, len(tool_calls), iteration + 1)
                
                # Save tool calls to log
                _save_api_log(self.hass, f"tool_calls_iter_{iteration + 1}", {
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration + 1,
                    "tool_calls": [
                        {
                            "name": getattr(tc, "name", None),
                            "arguments": getattr(tc, "arguments", None),
                        }
                        for tc in tool_calls
                    ],
                })
                
                tool_results = []
                
                for tool_call in tool_calls:
                    try:
                        tool_name = getattr(tool_call, "name", None)
                        arguments_str = getattr(tool_call, "arguments", "{}")
                        
                        if not tool_name:
                            _LOGGER.warning("[v%s] Invalid tool call: missing name", INTEGRATION_VERSION)
                            continue
                        
                        _LOGGER.info("[v%s] Executing tool: %s", INTEGRATION_VERSION, tool_name)
                        
                        try:
                            arguments = json.loads(arguments_str)
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        # Find and execute the matching function
                        from . import get_functions_from_options
                        functions = get_functions_from_options(opts)
                        matching_func = next((f for f in functions if f["spec"]["name"] == tool_name), None)
                        
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
                            # Wrap result in proper structure
                            result_data = {"ok": True, "result": result} if not isinstance(result, dict) else result
                            _LOGGER.info("[v%s] Tool %s executed successfully", INTEGRATION_VERSION, tool_name)
                        else:
                            # Check if it's a Home Assistant LLM API tool
                            if chat_log.llm_api:
                                try:
                                    from homeassistant.helpers import llm
                                    tool_input = llm.ToolInput(
                                        tool_name=tool_name,
                                        tool_args=arguments,
                                        platform=DOMAIN,
                                        context=user_input.context,
                                        user_prompt=user_input.text,
                                        language=user_input.language,
                                        assistant=conversation.DOMAIN,
                                        device_id=user_input.device_id,
                                    )
                                    result = await chat_log.llm_api.async_call_tool(tool_input)
                                    result_data = {"ok": True, "result": result}
                                    _LOGGER.info("[v%s] HA LLM API tool %s executed successfully", INTEGRATION_VERSION, tool_name)
                                except Exception as e:
                                    _LOGGER.error("[v%s] Failed to execute HA LLM API tool %s: %s", INTEGRATION_VERSION, tool_name, e)
                                    result_data = {"ok": False, "error": str(e)}
                            else:
                                _LOGGER.warning("[v%s] No matching tool found for: %s", INTEGRATION_VERSION, tool_name)
                                result_data = {"ok": False, "error": f"Unknown tool: {tool_name}"}
                        
                        # Add tool result in Responses API format
                        tool_results.append({
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": result_data
                        })
                        
                    except Exception as e:
                        _LOGGER.error("[v%s] Failed to execute tool call: %s", INTEGRATION_VERSION, e)
                        if tool_name:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "result": {"ok": False, "error": str(e)}
                            })
                
                if not tool_results:
                    # No results to send back, break to avoid infinite loop
                    break
                
                # Save tool results to log
                _save_api_log(self.hass, f"tool_results_iter_{iteration + 1}", {
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration + 1,
                    "tool_results": tool_results,
                })
                
                # Per Responses API spec: send ONLY tool results as next input
                # The API maintains conversation state internally
                kwargs["input"] = tool_results
                
                _LOGGER.debug("[v%s] Continuing loop with %d tool results", INTEGRATION_VERSION, len(tool_results))
            
            # Parse final response text
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
                _LOGGER.debug("[v%s] Parsed final response text: %s", INTEGRATION_VERSION, out[:100] + "..." if len(out) > 100 else out)
            except Exception as e:
                _LOGGER.error("[v%s] Error parsing response structure: %s", INTEGRATION_VERSION, e)
                out = ""
        
        # Fallback: If the model returned JSON in output_text, try to parse and execute
        if out and (out.strip().startswith("[") or out.strip().startswith("{")):
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


