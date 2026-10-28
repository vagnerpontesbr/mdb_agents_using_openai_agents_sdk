"""Buffered Responses API provider for Engine Tool Pod execution only."""

import asyncio
from dataclasses import dataclass
import json
import os

from agent_engine_sdk.models import LLMResponse, LLMStreamChunk, LLMTokenUsage, LLMToolCall, ToolCallChunk
from openai import AsyncOpenAI

from .adapter import UnsupportedContract


@dataclass(frozen=True)
class OpenAIModelConfig:
    model: str = "gpt-5.6-luna"


class OpenAIProvider:
    def __init__(self, config, *, tools=None, tool_choice=None):
        self.config = config
        self.tools = []
        for tool in tools or []:
            function = tool.function
            if tool.type != "function" or not isinstance(function, dict):
                raise UnsupportedContract("Only function tools are supported")
            self.tools.append({"type": "function", **function, "strict": False})
        if tool_choice not in (None, "auto"):
            raise UnsupportedContract("Forced tool choice is not implemented")

    async def ainvoke(self, messages, *, stop=None, **options):
        if os.environ.get("RUNNER_MODE") not in {"tool", "tool_function"}:
            raise UnsupportedContract("Provider execution requires the Engine Tool Pod")
        if stop or set(options) - {"parallel_tool_calls", "max_tokens"}:
            raise UnsupportedContract("Unsupported provider options")
        if options.get("parallel_tool_calls") not in (None, False):
            raise UnsupportedContract("Parallel tools are unsupported")
        inputs = []
        for message in messages:
            if message.role not in {"system", "user"} or not isinstance(message.content, str):
                raise UnsupportedContract("Only initial text messages are supported")
            inputs.append({"role": message.role, "content": message.content})
        limit = options.get("max_tokens", 2048)
        if type(limit) is not int or not 1 <= limit <= 2048:
            raise UnsupportedContract("Output budget must be between 1 and 2048 tokens")
        # Read injected credentials at call time, inside Engine credential
        # isolation; do not retain them in process-global client instances.
        async with AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.openai.com/v1",
            max_retries=0, timeout=60.0,
        ) as client:
            response = await client.responses.create(
                model=self.config.model, input=inputs, tools=self.tools,
                parallel_tool_calls=False, max_output_tokens=limit, store=False,
            )
        if response.status != "completed":
            raise UnsupportedContract("Provider response did not complete")
        calls = []
        text = []
        for item in response.output:
            if item.type == "function_call":
                args = json.loads(item.arguments)
                if not isinstance(args, dict) or not item.call_id:
                    raise UnsupportedContract("Invalid provider tool call")
                calls.append(LLMToolCall(id=item.call_id, name=item.name, args=args, type="tool_call"))
            elif item.type == "message":
                for block in item.content:
                    if block.type != "output_text":
                        raise UnsupportedContract("Provider refused or returned unsupported content")
                    text.append(block.text)
            elif item.type != "reasoning":
                raise UnsupportedContract("Unsupported provider output item")
        # Reasoning items are not exported as text or stored by this adapter.
        # This single-call version never attempts continuation without them.
        if len(calls) > 1:
            raise UnsupportedContract("Multiple tool calls are unsupported")
        usage = response.usage
        return LLMResponse(content="".join(text), tool_calls=calls or None, id=response.id,
                           usage=LLMTokenUsage(input_tokens=usage.input_tokens,
                                               output_tokens=usage.output_tokens,
                                               total_tokens=usage.total_tokens) if usage else None)

    def invoke(self, messages, **kwargs):
        return asyncio.run(self.ainvoke(messages, **kwargs))

    async def astream(self, messages, **kwargs):
        response = await self.ainvoke(messages, **kwargs)
        yield LLMStreamChunk(
            id=response.id, content=response.content, usage=response.usage,
            tool_calls=[ToolCallChunk(id=c.id, name=c.name, args=json.dumps(c.args), index=i)
                        for i, c in enumerate(response.tool_calls or [])] or None,
        )


def provider_factory(config, **kwargs):
    return OpenAIProvider(config, **kwargs)
