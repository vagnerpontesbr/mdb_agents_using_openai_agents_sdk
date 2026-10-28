"""Pinned runtime loader/stream contracts, without starting a server."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_engine_sdk.models import AgentInput, LLMResponse, LLMToolCall, RequestContext
from agent_engine_runner_shared import hooks
from agent_engine_runner_shared.context import set_execution_context, clear_execution_context
from agent_engine_runner_shared.runtime import TenantRuntime
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper
from agent_engine_runner_shared.server.aer import AERServer
from agents.exceptions import UserError
from pydantic import BaseModel, ConfigDict

from openai_engine_adapter.adapter import RemoteReadTool, UnsupportedContract
from openai_engine_adapter.app import OpenAIEngineApp


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_minor: int
    currency: str


class LoaderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        hooks.reset_hooks()
        self.app = OpenAIEngineApp(
            name="invoice-probe", instructions="Read synthetic invoices only.",
            llm_id="invoice-model", model_name="configured-model",
            provider_builder=lambda: object(), provider_adapter_factory=lambda model, **kw: model,
        )
        self.app.tool(contract=RemoteReadTool("lookup_invoice", "Read invoice", Args, Result))(
            lambda invoice_id: {"amount_minor": 7990, "currency": "USD"}
        )
        self.ctx = RequestContext(execution_id="exec-1", user_id="user-1",
                                  session_id="session-1", workspace_id="workspace-1")
        self.wrapper = SecureToolWrapper("https://oe.invalid", "exec-1")
        self.tokens = set_execution_context(
            execution_id="exec-1", wrapper=self.wrapper, oe_url="https://oe.invalid",
            user_id="user-1", session_id="session-1", workspace_id="workspace-1",
        )

    def tearDown(self):
        clear_execution_context(self.tokens)
        hooks.reset_hooks()

    async def test_actual_runtime_dispatch_and_stream_parser(self):
        agent = TenantRuntime.get_agent(SimpleNamespace(_graph_builder=self.app))
        reply = LLMResponse(content="", tool_calls=[LLMToolCall(
            id="call-1", name="lookup_invoice", args={"invoice_id": "demo-1"},
        )])
        with patch.object(SecureLLMProxy, "invoke", return_value=reply), patch.object(
            self.wrapper, "execute_tool", return_value={"amount_minor": 7990, "currency": "USD"},
        ) as tool:
            # Real stream consumer needs no initialized server for terminal-only output.
            result = await AERServer._execute_via_agent_stream(
                SimpleNamespace(), agent, self.ctx, AgentInput(payload={"message": "Read demo-1"}),
                "https://oe.invalid", "exec-1",
            )
        self.assertEqual(json.loads(result.content), {"amount_minor": 7990, "currency": "USD"})
        tool.assert_called_once_with("lookup_invoice", {"invoice_id": "demo-1"},
                                     tool_call_id="call-1", is_local=False)
        self.assertIsNone(hooks.get_workflow_adapter())
        self.assertIsNone(hooks.get_suspend_handler())

    async def test_actual_stream_parser_propagates_tool_denial(self):
        agent = self.app.get_agent()
        reply = LLMResponse(content="", tool_calls=[LLMToolCall(
            id="call-1", name="lookup_invoice", args={"invoice_id": "demo-1"},
        )])
        with patch.object(SecureLLMProxy, "invoke", return_value=reply), patch.object(
            self.wrapper, "execute_tool", side_effect=PermissionError("synthetic policy denial"),
        ) as tool, self.assertRaises(UserError):
            await AERServer._execute_via_agent_stream(
                SimpleNamespace(), agent, self.ctx, AgentInput(payload={"message": "Read demo-1"}),
                "https://oe.invalid", "exec-1",
            )
        tool.assert_called_once()

    async def test_payload_cannot_override_platform_context(self):
        agent = self.app.get_agent()
        with self.assertRaises(UnsupportedContract):
            await agent.execute(self.ctx, AgentInput(payload={"message": "x", "user_id": "other"}))
        with self.assertRaises(UnsupportedContract):
            await agent.execute(self.ctx.model_copy(update={"user_id": "other"}),
                                AgentInput(payload={"message": "x"}))

    async def test_tool_discovery_rebuilds_registry_without_duplicate(self):
        self.app.get_agent()
        provider = hooks.get_named_llm("invoice-model")
        self.app.get_agent()
        hooks.reset_llm_registry()
        self.app.get_agent()
        self.assertIs(hooks.get_named_llm("invoice-model"), provider)

    async def test_run_registers_remote_tool_and_real_app(self):
        with patch("agent_engine_runner_shared.runtime.TenantRuntime", autospec=True) as runtime:
            self.app.run()
        runtime.return_value.register_and_run.assert_called_once_with(self.app)
        args = runtime.return_value.register_tool.call_args.args
        self.assertEqual(args[0], "lookup_invoice")
        self.assertFalse(args[2]["is_local"])
        self.assertEqual(args[1](invoice_id="demo-1"), {"amount_minor": 7990, "currency": "USD"})


if __name__ == "__main__":
    unittest.main()
