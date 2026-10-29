"""One model call and at most one remote read tool; no hosted support claim.

Bindings MUST be supplied by trusted Engine runtime plumbing for this request.
No credentials, direct provider transport, memory writer, approval store or
retry mechanism lives here. Tools must be provisioned read-only in Engine;
Python registration alone cannot establish backend authorization.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Callable

from agents import Agent, FunctionTool, Model, ModelSettings, RunConfig, Runner
from agents.items import ModelResponse
from agents.usage import Usage
from agent_engine_sdk.models import (
    AgentInput, AgentOutput, LLMInvocationOptions, LLMResponse,
    LLMToolSchema, Message, RequestContext, StreamEvent,
)
from agent_engine_runner_shared.execution import AgentExecutionResult
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from pydantic import BaseModel


class UnsupportedContract(ValueError):
    """Requested behavior has no validated translation in this adapter."""


@dataclass(frozen=True)
class RemoteReadTool:
    """Trusted remote read registration, with strict application contracts."""

    name: str
    description: str
    arguments: type[BaseModel]
    result: type[BaseModel]

    def __post_init__(self):
        for model in (self.arguments, self.result):
            if model.model_config.get("extra") != "forbid":
                raise ValueError("Tool models must forbid extra fields")

    def schema(self):
        return LLMToolSchema(type="function", function={
            "name": self.name, "description": self.description,
            "parameters": self.arguments.model_json_schema(),
        })


@dataclass(frozen=True)
class EngineBindings:
    """Request-local Engine objects, already configured by trusted integration.

    The LLM must be bound to precisely the supplied schemas. The factory owns
    provider selection; this adapter never selects or changes the model/key.
    """

    llm: SecureLLMProxy
    tools: SecureToolWrapper

    @classmethod
    def from_runtime(cls, *, context, schemas, llm_id, model_name, managed_memory=False):
        """Reuse the AER-owned wrapper; never reconstruct its execution state."""
        from agent_engine_runner_shared.context import (
            get_current_wrapper, get_current_execution_id, get_current_user_id,
            get_current_session_id, get_current_workspace_id,
        )

        expected = (context.execution_id, context.user_id, context.session_id, context.workspace_id)
        actual = (get_current_execution_id(), get_current_user_id(),
                  get_current_session_id(), get_current_workspace_id())
        wrapper = get_current_wrapper()
        if actual != expected or wrapper is None or wrapper.execution_id != context.execution_id:
            raise UnsupportedContract("Missing or mismatched Engine execution context")
        if wrapper.durable_memory is not None and not managed_memory:
            raise UnsupportedContract("Managed memory requires the explicit memory integration")
        if managed_memory:
            from agent_engine_runner_shared.workflow import current_attempt_context
            from agent_engine_runner_shared.workflow.memory import validate_durable_memory_identity
            attempt = current_attempt_context()
            if attempt is None or wrapper.durable_memory is None:
                raise UnsupportedContract("Managed memory requires an Engine memory-enabled attempt")
            validate_durable_memory_identity(attempt.workflow_identity, context.user_id)
        return cls(SecureLLMProxy(
            oe_url=wrapper.oe_url, execution_id=context.execution_id,
            llm_id=llm_id, model_name=model_name, bound_tools=schemas,
            operational_steps=wrapper.operational_steps,
            durable_memory=wrapper.durable_memory,
        ), wrapper)

    @classmethod
    def for_request(cls, *, oe_url, context, schemas, llm_id, model_name):
        """Build real pinned proxies inside a trusted Engine execution.

        oe_url is deployment configuration, never caller payload or an owner
        URL supplied in a request. This does not create an OE execution or
        authenticate a public API caller. No network call occurs here.
        """
        wrapper = SecureToolWrapper(oe_url=oe_url, execution_id=context.execution_id)
        llm = SecureLLMProxy(
            oe_url=oe_url, execution_id=context.execution_id,
            llm_id=llm_id, model_name=model_name, bound_tools=schemas,
            operational_steps=wrapper.operational_steps,
        )
        return cls(llm, wrapper)


class EngineModel(Model):
    def __init__(self, bindings: EngineBindings, registrations):
        self.bindings = bindings
        self.registrations = registrations
        self.called = False

    async def get_response(
        self, system_instructions, input, model_settings, tools,
        output_schema, handoffs, tracing, *, previous_response_id,
        conversation_id, prompt,
    ):
        if self.called:
            raise UnsupportedContract("Multiple model turns are not supported")
        if output_schema or handoffs or previous_response_id or conversation_id or prompt:
            raise UnsupportedContract("Unsupported SDK continuation or output contract")
        if not tracing.is_disabled():
            raise UnsupportedContract("Independent SDK trace export is disabled")
        expected = ModelSettings(parallel_tool_calls=False).to_json_dict()
        if model_settings.to_json_dict() != expected:
            raise UnsupportedContract("Model settings must be configured by Engine")
        if {tool.name for tool in tools} != set(self.registrations):
            raise UnsupportedContract("SDK and Engine tool registries differ")
        if isinstance(input, str):
            user_text = input
        elif (len(input) == 1 and input[0].get("role") == "user"
              and isinstance(input[0].get("content"), str)):
            user_text = input[0]["content"]
        else:
            raise UnsupportedContract("Only a single text user turn is supported")
        messages = []
        if system_instructions:
            messages.append(Message(role="system", content=system_instructions))
        messages.append(Message(role="user", content=user_text))
        self.called = True
        # Engine's pinned interfaces are synchronous. Cancelling this await
        # does NOT cancel an already-running remote operation. No retry here.
        response = await asyncio.to_thread(
            self.bindings.llm.invoke, messages,
            options=LLMInvocationOptions(parallel_tool_calls=False),
        )
        if not isinstance(response, LLMResponse):
            raise UnsupportedContract("Expected typed Engine LLMResponse")
        calls = response.tool_calls or []
        if len(calls) > 1:
            raise UnsupportedContract("Parallel/multiple tools are not supported")
        output = []
        if calls:
            call = calls[0]
            if not call.id or not call.id.strip() or call.name not in self.registrations:
                raise UnsupportedContract("Missing call ID or unknown tool")
            if not isinstance(call.args, dict):
                raise UnsupportedContract("Tool arguments must be a JSON object")
            # Validate before Runner can invoke any tool. Preserve exact values;
            # do not coerce or silently insert defaults into the proposed action.
            registration = self.registrations[call.name]
            registration.arguments.model_validate(call.args, strict=True)
            output.append(ResponseFunctionToolCall(
                type="function_call", call_id=call.id, name=call.name,
                arguments=json.dumps(call.args, allow_nan=False),
            ))
        else:
            output.append(ResponseOutputMessage(
                id=response.id or "adapter-text", type="message", role="assistant",
                status="completed", content=[ResponseOutputText(
                    type="output_text", text=response.content, annotations=[],
                )],
            ))
        counts = response.usage.to_langchain_usage_metadata() if response.usage else {}
        return ModelResponse(
            output=output, response_id=None,
            usage=Usage(requests=1, input_tokens=counts.get("input_tokens", 0),
                        output_tokens=counts.get("output_tokens", 0),
                        total_tokens=counts.get("total_tokens", 0)),
        )

    async def stream_response(self, *args, **kwargs):
        raise UnsupportedContract("Token streaming is not implemented")
        yield  # Marks this method as an async iterator.


class OpenAIEngineAgent:
    """Engine BaseAgent contract backed by the real OpenAI Runner.

    This is an integration library, not a deployable BaseApp. No fake runtime
    workflow/suspend hooks are registered. A trusted factory receives a copied
    request context and tool schemas; it must bind Engine proxies per request.
    """

    def __init__(
        self, *, instructions: str, tools: tuple[RemoteReadTool, ...],
        bindings_factory: Callable[[RequestContext, list[LLMToolSchema]], EngineBindings],
    ):
        self.instructions = instructions
        self.registrations = {tool.name: tool for tool in tools}
        if len(self.registrations) != len(tools):
            raise ValueError("Duplicate tool names")
        self.bindings_factory = bindings_factory

    def execute(self, ctx: RequestContext, input: AgentInput) -> AgentExecutionResult:
        context = ctx.model_copy(deep=True)
        for field in ("execution_id", "user_id", "session_id", "workspace_id"):
            value = getattr(context, field)
            if not value or not value.strip():
                raise UnsupportedContract("Trusted execution/user/session/workspace required")
        if (context.resume or context.resume_data is not None
                or context.previous_execution_cancelled or context.metadata):
            raise UnsupportedContract("Resume, recovery and opaque state are unsupported")
        payload = input.payload
        if (not isinstance(payload, dict) or set(payload) != {"text"}
                or not isinstance(payload["text"], str) or not payload["text"].strip()
                or len(payload["text"]) > 16000):
            raise UnsupportedContract("Expected only nonempty text, at most 16000 characters")
        text = payload["text"]
        consumed = False

        async def invoke():
            nonlocal consumed
            if consumed:
                raise UnsupportedContract("ExecutionResult is single-use")
            consumed = True
            bindings = self.bindings_factory(
                context, [tool.schema() for tool in self.registrations.values()],
            )
            sdk_tools = []
            for registration in self.registrations.values():
                async def run_tool(tool_context, arguments, registration=registration):
                    args = json.loads(arguments)
                    registration.arguments.model_validate(args, strict=True)
                    result = await asyncio.to_thread(
                        bindings.tools.execute_tool, registration.name, args,
                        tool_call_id=tool_context.tool_call_id, is_local=False,
                    )
                    # Tool content is never interpreted as an approval/resume
                    # control message. Nonconforming results fail validation.
                    validated = (registration.result.model_validate_json(result, strict=True) if isinstance(result, str)
                                 else registration.result.model_validate(result, strict=True))
                    return validated.model_dump_json()

                sdk_tools.append(FunctionTool(
                    name=registration.name, description=registration.description,
                    params_json_schema=registration.arguments.model_json_schema(),
                    on_invoke_tool=run_tool, strict_json_schema=False,
                ))
            agent = Agent(
                name="EngineReadAdapter", instructions=self.instructions,
                model=EngineModel(bindings, self.registrations), tools=sdk_tools,
                model_settings=ModelSettings(parallel_tool_calls=False),
                tool_use_behavior="stop_on_first_tool",
            )
            result = await Runner.run(
                agent, text, context=context, max_turns=1,
                run_config=RunConfig(tracing_disabled=True),
            )
            return AgentOutput(response={"output": result.final_output})

        async def stream():
            output = await invoke()
            # AER consumes response, not the library's output envelope.
            yield StreamEvent(event="result", data={"response": output.response["output"]})

        return AgentExecutionResult(invoke, stream)
