"""Custom BaseApp loader; provider construction stays in the Engine Tool Pod."""

import json

from agent_engine_sdk import BaseApp
from agent_engine_sdk.models import AgentInput, ToolDefinition
from agent_engine_runner_shared import hooks

from .adapter import EngineBindings, OpenAIEngineAgent, RemoteReadTool, UnsupportedContract


class RuntimeAgent:
    """Translate AER's normalized message without accepting caller identity."""

    def __init__(self, agent):
        self.agent = agent

    def execute(self, ctx, input):
        payload = input.payload
        if not isinstance(payload, dict) or set(payload) != {"message"}:
            raise UnsupportedContract("AER payload must contain only message")
        return self.agent.execute(ctx, AgentInput(payload={"text": payload["message"]}))


class OpenAIEngineApp(BaseApp):
    """Fixed read-tool registry and explicit Engine provider extension.

    provider_builder returns the raw model registered for Tool Pod discovery.
    provider_adapter_factory must implement Engine BaseLLM and bind its tools.
    No provider credential is required by the Runner. No fake suspend/replay
    hooks are registered. Construction does not start or instantiate runtime.
    """

    def __init__(self, *, name, instructions, llm_id, model_name,
                 provider_builder, provider_adapter_factory, review_action_factory=None, review_ttl_seconds=None, managed_memory=False):
        super().__init__(name)
        self.instructions = instructions
        self.llm_id = llm_id
        self.model_name = model_name
        self.provider_builder = provider_builder
        self.provider_adapter_factory = provider_adapter_factory
        self._registrations = {}
        self._provider = None
        self.review_action_factory = review_action_factory
        self.review_ttl_seconds = review_ttl_seconds
        self.managed_memory = managed_memory

    def tool(self, *, contract: RemoteReadTool):
        def register(function):
            if contract.name in self._registrations:
                raise ValueError("Duplicate tool name")

            def validated(**kwargs):
                contract.arguments.model_validate(kwargs, strict=True)
                result = function(**kwargs)
                validated = contract.result.model_validate(result, strict=True).model_dump(mode="json")
                # A JSON string survives Engine protobuf replay without dict
                # ordering/number-representation changes in its memory text.
                return json.dumps(validated, sort_keys=True, separators=(",", ":"), allow_nan=False) if self.managed_memory else validated

            self._registrations[contract.name] = (contract, validated)
            return function
        return register

    def get_tool_definitions(self):
        return [ToolDefinition(
            name=c.name, description=c.description, args_schema=c.arguments.model_json_schema(),
            callable=fn, remote=True,
        ) for c, fn in self._registrations.values()]

    def tools(self):
        return tuple(c for c, _ in self._registrations.values())

    def entrypoint(self, fn):
        raise UnsupportedContract("This bounded App uses its fixed Runner entrypoint")

    def get_agent(self, callbacks=None, *, graph=None):
        if graph is not None:
            raise UnsupportedContract("External graphs are unsupported")
        # ToolServer clears the named registry before discovery. Re-register
        # our model when absent; never clear other registrations here.
        with hooks.entrypoint_scope():
            registry = hooks.snapshot_llm_registry()
            if self.llm_id not in registry:
                if self._provider is None:
                    self._provider = self.provider_builder()
                hooks.register_llm(self.llm_id, self._provider)
            elif registry[self.llm_id] is not self._provider:
                raise UnsupportedContract("Conflicting Engine model registration")

        def bindings(context, schemas):
            return EngineBindings.from_runtime(context=context, schemas=schemas,
                                               llm_id=self.llm_id, model_name=self.model_name,
                                               managed_memory=self.managed_memory)

        # Model/tool audit is owned by Engine proxies. Optional graph-node
        # callbacks are not synthesized into replacement execution traces.
        agent = RuntimeAgent(OpenAIEngineAgent(
            instructions=self.instructions, tools=self.tools(), bindings_factory=bindings,
        ))
        if self.review_action_factory is not None:
            from .review_execution import ReviewExecutionAgent

            hooks.register_workflow_adapter("openai-engine-review", "3" if self.managed_memory else ("2" if self.review_ttl_seconds is not None else "1"))
            return ReviewExecutionAgent(agent, self.review_action_factory, ttl_seconds=self.review_ttl_seconds)
        return agent

    def run(self):
        from agent_engine_runner_shared.runtime import TenantRuntime

        hooks.register_llm_adapter_factory(self.provider_adapter_factory)
        runtime = TenantRuntime(app_name=self.name, app_version="0.0.1")
        for definition in self.get_tool_definitions():
            metadata = definition.model_dump(exclude={"callable"})
            metadata["is_local"] = False
            runtime.register_tool(definition.name, definition.callable, metadata)
        runtime.register_and_run(self)
