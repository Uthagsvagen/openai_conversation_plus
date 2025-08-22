"""The OpenAI Conversation integration."""

from __future__ import annotations

import json
import logging
from typing import Literal

from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai._exceptions import AuthenticationError, OpenAIError
from openai.types.chat.chat_completion import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
)
import yaml

from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    intent,
    template,
)
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid

from .const import (
    CONF_API_VERSION,
    CONF_ATTACH_USERNAME,
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CONTEXT_THRESHOLD,
    CONF_CONTEXT_TRUNCATE_STRATEGY,
    CONF_ENABLE_WEB_SEARCH,
    CONF_FUNCTIONS,
    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    CONF_MAX_TOKENS,
    CONF_ORGANIZATION,
    CONF_PROMPT,
    CONF_REASONING_LEVEL,
    CONF_SEARCH_CONTEXT_SIZE,
    CONF_SKIP_AUTHENTICATION,
    CONF_STORE_CONVERSATIONS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_USE_RESPONSE_API,
    CONF_USE_TOOLS,
    CONF_USER_LOCATION,
    CONF_VERBOSITY,
    DEFAULT_ATTACH_USERNAME,
    DEFAULT_CHAT_MODEL,
    DEFAULT_CONF_FUNCTIONS,
    DEFAULT_CONTEXT_THRESHOLD,
    DEFAULT_CONTEXT_TRUNCATE_STRATEGY,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_REASONING_LEVEL,
    DEFAULT_SEARCH_CONTEXT_SIZE,
    DEFAULT_SKIP_AUTHENTICATION,
    DEFAULT_STORE_CONVERSATIONS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_USE_RESPONSE_API,
    DEFAULT_USE_TOOLS,
    DEFAULT_USER_LOCATION,
    DEFAULT_VERBOSITY,
    DOMAIN,
    EVENT_CONVERSATION_FINISHED,
    GPT5_MODELS,
)
from .exceptions import (
    FunctionLoadFailed,
    FunctionNotFound,
    InvalidFunction,
    ParseArgumentsFailed,
    TokenLengthExceededError,
)
from .helpers import get_function_executor, is_azure, validate_authentication
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Platform list
PLATFORMS = ["ai_task"]

# hass.data key for agent.
DATA_AGENT = "agent"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up OpenAI Conversation."""
    await async_setup_services(hass, config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenAI Conversation from a config entry."""

    try:
        await validate_authentication(
            hass=hass,
            api_key=entry.data[CONF_API_KEY],
            base_url=entry.data.get(CONF_BASE_URL),
            api_version=entry.data.get(CONF_API_VERSION),
            organization=entry.data.get(CONF_ORGANIZATION),
            skip_authentication=entry.data.get(
                CONF_SKIP_AUTHENTICATION, DEFAULT_SKIP_AUTHENTICATION
            ),
        )
    except AuthenticationError as err:
        _LOGGER.error("Invalid API key: %s", err)
        return False
    except OpenAIError as err:
        raise ConfigEntryNotReady(err) from err

    agent = OpenAIAgent(hass, entry)

    data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    data[CONF_API_KEY] = entry.data[CONF_API_KEY]
    data[DATA_AGENT] = agent

    conversation.async_set_agent(hass, entry, agent)
    
    # Forward the entry to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenAI."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        conversation.async_unset_agent(hass, entry)
    return unload_ok


class OpenAIAgent(conversation.AbstractConversationAgent):
    """OpenAI conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        base_url = entry.data.get(CONF_BASE_URL)
        if is_azure(base_url):
            self.client = AsyncAzureOpenAI(
                api_key=entry.data[CONF_API_KEY],
                azure_endpoint=base_url,
                api_version=entry.data.get(CONF_API_VERSION),
                organization=entry.data.get(CONF_ORGANIZATION),
                http_client=get_async_client(hass),
            )
        else:
            self.client = AsyncOpenAI(
                api_key=entry.data[CONF_API_KEY],
                base_url=base_url,
                organization=entry.data.get(CONF_ORGANIZATION),
                http_client=get_async_client(hass),
            )
        # Cache current platform data which gets added to each request (caching done by library)
        _ = hass.async_add_executor_job(self.client.platform_headers)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        exposed_entities = self.get_exposed_entities()

        if user_input.conversation_id in self.history:
            conversation_id = user_input.conversation_id
            messages = self.history[conversation_id]
        else:
            conversation_id = ulid.ulid()
            user_input.conversation_id = conversation_id
            try:
                system_message = self._generate_system_message(
                    exposed_entities, user_input
                )
            except TemplateError as err:
                _LOGGER.error("Error rendering prompt: %s", err)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Sorry, I had a problem with my template: {err}",
                )
                return conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )
            messages = [system_message]
        user_message = {"role": "user", "content": user_input.text}
        if self.entry.options.get(CONF_ATTACH_USERNAME, DEFAULT_ATTACH_USERNAME):
            user = user_input.context.user_id
            if user is not None:
                user_message[ATTR_NAME] = user

        messages.append(user_message)

        try:
            query_response = await self.query(user_input, messages, exposed_entities, 0)
        except OpenAIError as err:
            _LOGGER.error(err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem talking to OpenAI: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )
        except HomeAssistantError as err:
            _LOGGER.error(err, exc_info=err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Something went wrong: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        messages.append(query_response.message.model_dump(exclude_none=True))
        self.history[conversation_id] = messages

        self.hass.bus.async_fire(
            EVENT_CONVERSATION_FINISHED,
            {
                "response": query_response.response.model_dump(),
                "user_input": user_input,
                "messages": messages,
            },
        )

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(query_response.message.content)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _generate_system_message(
        self, exposed_entities, user_input: conversation.ConversationInput
    ):
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        prompt = self._async_generate_prompt(raw_prompt, exposed_entities, user_input)
        return {"role": "system", "content": prompt}

    def _async_generate_prompt(
        self,
        raw_prompt: str,
        exposed_entities,
        user_input: conversation.ConversationInput,
    ) -> str:
        """Generate a prompt for the user."""
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
                "exposed_entities": exposed_entities,
                "current_device_id": user_input.device_id,
            },
            parse_result=False,
        )

    def get_exposed_entities(self):
        states = [
            state
            for state in self.hass.states.async_all()
            if async_should_expose(self.hass, conversation.DOMAIN, state.entity_id)
        ]
        entity_registry = er.async_get(self.hass)
        exposed_entities = []
        for state in states:
            entity_id = state.entity_id
            entity = entity_registry.async_get(entity_id)

            aliases = []
            if entity and entity.aliases:
                aliases = entity.aliases

            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                }
            )
        return exposed_entities

    def get_functions(self):
        try:
            function = self.entry.options.get(CONF_FUNCTIONS)
            result = yaml.safe_load(function) if function else DEFAULT_CONF_FUNCTIONS
            if result:
                for setting in result:
                    function_executor = get_function_executor(
                        setting["function"]["type"]
                    )
                    setting["function"] = function_executor.to_arguments(
                        setting["function"]
                    )
            return result
        except (InvalidFunction, FunctionNotFound) as e:
            raise e
        except:
            raise FunctionLoadFailed()

    async def truncate_message_history(
        self, messages, exposed_entities, user_input: conversation.ConversationInput
    ):
        """Truncate message history."""
        strategy = self.entry.options.get(
            CONF_CONTEXT_TRUNCATE_STRATEGY, DEFAULT_CONTEXT_TRUNCATE_STRATEGY
        )

        if strategy == "clear":
            last_user_message_index = None
            for i in reversed(range(len(messages))):
                if messages[i]["role"] == "user":
                    last_user_message_index = i
                    break

            if last_user_message_index is not None:
                del messages[1:last_user_message_index]
                # refresh system prompt when all messages are deleted
                messages[0] = self._generate_system_message(
                    exposed_entities, user_input
                )

    async def query(
        self,
        user_input: conversation.ConversationInput,
        messages,
        exposed_entities,
        n_requests,
    ) -> OpenAIQueryResponse:
        """Process a sentence."""
        model = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        max_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TOP_P)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        use_tools = self.entry.options.get(CONF_USE_TOOLS, DEFAULT_USE_TOOLS)
        context_threshold = self.entry.options.get(
            CONF_CONTEXT_THRESHOLD, DEFAULT_CONTEXT_THRESHOLD
        )
        functions = list(map(lambda s: s["spec"], self.get_functions()))
        function_call = "auto"
        if n_requests == self.entry.options.get(
            CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
            DEFAULT_MAX_FUNCTION_CALLS_PER_CONVERSATION,
        ):
            function_call = "none"

        tool_kwargs = {"functions": functions, "function_call": function_call}
        if use_tools:
            tool_kwargs = {
                "tools": [{"type": "function", "function": func} for func in functions],
                "tool_choice": function_call,
            }

        if len(functions) == 0:
            tool_kwargs = {}

        # Check if we should use Response API
        use_response_api = self.entry.options.get(CONF_USE_RESPONSE_API, DEFAULT_USE_RESPONSE_API)
        
        # Add reasoning level and verbosity for GPT-5 models
        reasoning_level = self.entry.options.get(CONF_REASONING_LEVEL, DEFAULT_REASONING_LEVEL)
        verbosity = self.entry.options.get(CONF_VERBOSITY, DEFAULT_VERBOSITY)
        
        if use_response_api and hasattr(self.client, 'responses'):
            # Build tools list for Response API
            api_tools = []
            
            # Add custom functions as tools
            if tool_kwargs.get("tools"):
                api_tools.extend(tool_kwargs["tools"])
            
            # Add web search if enabled
            if self.entry.options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH):
                web_search_tool = {
                    "type": "web_search_preview",
                    "search_context_size": self.entry.options.get(CONF_SEARCH_CONTEXT_SIZE, DEFAULT_SEARCH_CONTEXT_SIZE)
                }
                
                # Add user location if configured
                user_location = self.entry.options.get(CONF_USER_LOCATION, DEFAULT_USER_LOCATION)
                if user_location and any(user_location.values()):
                    web_search_tool["user_location"] = {
                        "type": "approximate",
                        "country": user_location.get("country", ""),
                        "city": user_location.get("city", ""),
                        "region": user_location.get("region", "")
                    }
                
                api_tools.append(web_search_tool)
            
            # Check for previous response ID for conversation continuity
            previous_response_id = None
            if hasattr(user_input, 'agent_response_id'):
                previous_response_id = user_input.agent_response_id
            
            # Use Response API
            response_kwargs = {
                "model": model,
                "messages": messages,  # Response API uses 'messages' not 'input'
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }
            
            # Add GPT-5 specific parameters
            if model in GPT5_MODELS:
                response_kwargs["reasoning_effort"] = reasoning_level
                response_kwargs["verbosity"] = verbosity
            
            if api_tools:
                response_kwargs["tools"] = api_tools
                response_kwargs["tool_choice"] = tool_kwargs.get("tool_choice", "auto")
            
            if previous_response_id:
                response_kwargs["previous_response_id"] = previous_response_id
            
            # Add store parameter for conversation persistence
            response_kwargs["store"] = self.entry.options.get(CONF_STORE_CONVERSATIONS, DEFAULT_STORE_CONVERSATIONS)
            
            try:
                response = await self.client.responses.create(**response_kwargs)
                _LOGGER.info("Response API Prompt for %s: %s", model, json.dumps(messages))
                
                # Store response ID for conversation continuity
                if hasattr(response, 'id'):
                    user_input.agent_response_id = response.id
                
                # Handle Response API response format
                # The Response API maintains backward compatibility with Chat Completions
                # so the response structure should be similar
                if hasattr(response, 'choices') and response.choices:
                    choice = response.choices[0]
                    message = choice.message
                    
                    # Handle web search citations if present
                    if hasattr(message, 'annotations') and message.annotations:
                        # Process citations and add to content
                        citations = []
                        for annotation in message.annotations:
                            if annotation.type == "cite" and hasattr(annotation, 'url'):
                                citations.append(f"[{annotation.text}]({annotation.url})")
                        
                        if citations:
                            message.content += "\n\nSources:\n" + "\n".join(citations)
                    
                    return OpenAIQueryResponse(response=response, message=message)
                else:
                    # Fallback if response structure is unexpected
                    raise OpenAIError("Unexpected Response API format")
                    
            except AttributeError:
                # Response API not available, fall back to Chat Completions
                _LOGGER.info("Response API not available, using Chat Completions API")
                use_response_api = False
        
        if not use_response_api:
            # Use Chat Completions API (existing code)
            # Check if streaming is requested
            if self.entry.options.get("enable_streaming", False):
                # Streaming implementation
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    temperature=temperature,
                    user=user_input.conversation_id,
                    stream=True,
                    **tool_kwargs,
                )
                
                # Collect the streamed response
                collected_messages = []
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        collected_messages.append(chunk.choices[0].delta.content)
                
                # Create a complete response from streamed chunks
                complete_content = "".join(collected_messages)
                
                # Create a ChatCompletion-like response
                from openai.types.chat import ChatCompletionMessage
                from openai.types.chat.chat_completion import Choice, CompletionUsage
                
                message = ChatCompletionMessage(
                    role="assistant",
                    content=complete_content,
                    function_call=None,
                    tool_calls=None
                )
                
                choice = Choice(
                    finish_reason="stop",
                    index=0,
                    message=message
                )
                
                # Create usage data (approximate)
                usage = CompletionUsage(
                    completion_tokens=len(complete_content.split()),
                    prompt_tokens=sum(len(m.get("content", "").split()) for m in messages),
                    total_tokens=0
                )
                usage.total_tokens = usage.completion_tokens + usage.prompt_tokens
                
                response = ChatCompletion(
                    id="stream-" + ulid.ulid(),
                    choices=[choice],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion",
                    usage=usage
                )
            else:
                # Non-streaming implementation
                response: ChatCompletion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    temperature=temperature,
                    user=user_input.conversation_id,
                    **tool_kwargs,
                )
        
        _LOGGER.info("Prompt for %s: %s", model, json.dumps(messages))

        if response.usage.total_tokens > context_threshold:
            await self.truncate_message_history(messages, exposed_entities, user_input)

        choice: Choice = response.choices[0]
        message = choice.message

        if choice.finish_reason == "function_call":
            return await self.execute_function_call(
                user_input, messages, message, exposed_entities, n_requests + 1
            )
        if choice.finish_reason == "tool_calls":
            return await self.execute_tool_calls(
                user_input, messages, message, exposed_entities, n_requests + 1
            )
        if choice.finish_reason == "length":
            raise TokenLengthExceededError(response.usage.completion_tokens)

        return OpenAIQueryResponse(response=response, message=message)

    async def execute_function_call(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
    ) -> OpenAIQueryResponse:
        function_name = message.function_call.name
        function = next(
            (s for s in self.get_functions() if s["spec"]["name"] == function_name),
            None,
        )
        if function is not None:
            return await self.execute_function(
                user_input,
                messages,
                message,
                exposed_entities,
                n_requests,
                function,
            )
        raise FunctionNotFound(function_name)

    async def execute_function(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
        function,
    ) -> OpenAIQueryResponse:
        function_executor = get_function_executor(function["function"]["type"])

        try:
            arguments = json.loads(message.function_call.arguments)
        except json.decoder.JSONDecodeError as err:
            raise ParseArgumentsFailed(message.function_call.arguments) from err

        result = await function_executor.execute(
            self.hass, function["function"], arguments, user_input, exposed_entities
        )

        messages.append(
            {
                "role": "function",
                "name": message.function_call.name,
                "content": str(result),
            }
        )
        return await self.query(user_input, messages, exposed_entities, n_requests)

    async def execute_tool_calls(
        self,
        user_input: conversation.ConversationInput,
        messages,
        message: ChatCompletionMessage,
        exposed_entities,
        n_requests,
    ) -> OpenAIQueryResponse:
        messages.append(message.model_dump(exclude_none=True))
        for tool in message.tool_calls:
            function_name = tool.function.name
            function = next(
                (s for s in self.get_functions() if s["spec"]["name"] == function_name),
                None,
            )
            if function is not None:
                result = await self.execute_tool_function(
                    user_input,
                    tool,
                    exposed_entities,
                    function,
                )

                messages.append(
                    {
                        "tool_call_id": tool.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(result),
                    }
                )
            else:
                raise FunctionNotFound(function_name)
        return await self.query(user_input, messages, exposed_entities, n_requests)

    async def execute_tool_function(
        self,
        user_input: conversation.ConversationInput,
        tool,
        exposed_entities,
        function,
    ) -> OpenAIQueryResponse:
        function_executor = get_function_executor(function["function"]["type"])

        try:
            arguments = json.loads(tool.function.arguments)
        except json.decoder.JSONDecodeError as err:
            raise ParseArgumentsFailed(tool.function.arguments) from err

        result = await function_executor.execute(
            self.hass, function["function"], arguments, user_input, exposed_entities
        )
        return result


class OpenAIQueryResponse:
    """OpenAI query response value object."""

    def __init__(
        self, response: ChatCompletion, message: ChatCompletionMessage
    ) -> None:
        """Initialize OpenAI query response value object."""
        self.response = response
        self.message = message