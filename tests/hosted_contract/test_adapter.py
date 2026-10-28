"""Real Runner + signature-checked Engine doubles; no OE/provider calls."""

import asyncio
import json
import unittest
from unittest.mock import create_autospec

from agents.exceptions import UserError

from agent_engine_sdk.interfaces import BaseAgent
from agent_engine_sdk.models import AgentInput, LLMResponse, LLMToolCall, RequestContext
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper
from pydantic import BaseModel, ConfigDict, ValidationError

from openai_engine_adapter import EngineBindings, OpenAIEngineAgent, RemoteReadTool
from openai_engine_adapter.adapter import UnsupportedContract


class InvoiceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str


class InvoiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str
    amount_minor: int
    currency: str


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm = create_autospec(SecureLLMProxy, instance=True)
        self.wrapper = create_autospec(SecureToolWrapper, instance=True)
        self.llm.invoke.return_value = LLMResponse(content="", tool_calls=[
            LLMToolCall(id="call-1", name="lookup_invoice", args={"invoice_id": "demo-1"}),
        ])
        self.wrapper.execute_tool.return_value = {
            "invoice_id": "demo-1", "amount_minor": 7990, "currency": "USD",
        }
        self.context = RequestContext(execution_id="exec-1", user_id="user-1",
                                      session_id="session-1", workspace_id="workspace-1")
        self.factory_calls = []

        def factory(ctx, schemas):
            self.factory_calls.append((ctx, schemas))
            return EngineBindings(self.llm, self.wrapper)

        self.tool = RemoteReadTool("lookup_invoice", "Read a synthetic invoice",
                                   InvoiceArgs, InvoiceResult)
        self.agent = OpenAIEngineAgent(instructions="Read synthetic invoices only.",
                                      tools=(self.tool,), bindings_factory=factory)
        self.input = AgentInput(payload={"text": "Read invoice demo-1"})

    async def test_real_runner_routes_model_and_tool(self):
        self.assertIsInstance(self.agent, BaseAgent)
        output = await self.agent.execute(self.context, self.input)
        self.assertEqual(json.loads(output.response["output"]), self.wrapper.execute_tool.return_value)
        self.wrapper.execute_tool.assert_called_once_with(
            "lookup_invoice", {"invoice_id": "demo-1"}, tool_call_id="call-1", is_local=False,
        )
        self.llm.invoke.assert_called_once()
        messages = self.llm.invoke.call_args.args[0]
        self.assertEqual([m.role for m in messages], ["system", "user"])
        self.assertEqual(messages[-1].content, "Read invoice demo-1")
        self.assertEqual(self.factory_calls[0][1][0].function["name"], "lookup_invoice")

    async def test_text_response(self):
        self.llm.invoke.return_value = LLMResponse(content="Please specify an invoice.")
        output = await self.agent.execute(self.context, self.input)
        self.assertEqual(output.response["output"], "Please specify an invoice.")
        self.wrapper.execute_tool.assert_not_called()

    async def test_denial_propagates_without_retry(self):
        self.wrapper.execute_tool.side_effect = PermissionError("synthetic Engine denial")
        with self.assertRaises(UserError) as error:
            await self.agent.execute(self.context, self.input)
        self.assertIsInstance(error.exception.__cause__, PermissionError)
        self.wrapper.execute_tool.assert_called_once()
        self.llm.invoke.assert_called_once()

    async def test_model_failure_propagates_without_tool(self):
        self.llm.invoke.side_effect = TimeoutError("synthetic timeout")
        with self.assertRaises(TimeoutError):
            await self.agent.execute(self.context, self.input)
        self.llm.invoke.assert_called_once()
        self.wrapper.execute_tool.assert_not_called()

    async def test_invalid_model_calls_rejected_before_tool(self):
        cases = [
            [LLMToolCall(name="lookup_invoice", args={"invoice_id": "demo-1"})],
            [LLMToolCall(id="c", name="unknown", args={})],
            [LLMToolCall(id="c", name="lookup_invoice", args={"invoice_id": 1})],
            [LLMToolCall(id="c", name="lookup_invoice", args={"invoice_id": "x", "user_id": "other"})],
            [LLMToolCall(id="c", name="lookup_invoice", args="{}")],
            [LLMToolCall(id="c", name="lookup_invoice", args={})] * 2,
        ]
        for calls in cases:
            with self.subTest(calls=calls):
                self.llm.invoke.return_value = LLMResponse(content="", tool_calls=calls)
                with self.assertRaises((UnsupportedContract, ValidationError)):
                    await self.agent.execute(self.context, self.input)
        self.wrapper.execute_tool.assert_not_called()

    async def test_invalid_result_is_not_control_or_answer(self):
        self.wrapper.execute_tool.return_value = {"interrupted": True}
        with self.assertRaises(UserError) as error:
            await self.agent.execute(self.context, self.input)
        self.assertIsInstance(error.exception.__cause__, ValidationError)
        self.llm.invoke.assert_called_once()

    async def test_context_and_payload_fail_before_binding(self):
        for update in ({"resume": True}, {"resume_data": {}}, {"user_id": None},
                       {"previous_execution_cancelled": True}, {"metadata": {"state": "x"}}):
            with self.subTest(update=update), self.assertRaises(UnsupportedContract):
                await self.agent.execute(self.context.model_copy(update=update), self.input)
        for payload in ({"text": "x", "user_id": "other"}, {"text": ""}, {"text": "x" * 16001}):
            with self.assertRaises(UnsupportedContract):
                await self.agent.execute(self.context, AgentInput(payload=payload))
        self.assertEqual(self.factory_calls, [])

    async def test_single_terminal_event_and_single_use(self):
        result = self.agent.execute(self.context, self.input)
        events = [event async for event in result]
        self.assertEqual([event.event for event in events], ["result"])
        with self.assertRaises(UnsupportedContract):
            await result
        self.wrapper.execute_tool.assert_called_once()

    async def test_request_context_is_copied(self):
        execution = self.agent.execute(self.context, self.input)
        self.context.user_id = "changed"
        await execution
        self.assertEqual(self.factory_calls[0][0].user_id, "user-1")

    async def test_concurrent_runs_do_not_share_model_state(self):
        async def run(ctx):
            return await self.agent.execute(ctx, self.input)

        await asyncio.gather(
            run(self.context),
            run(self.context.model_copy(update={"user_id": "user-2"})),
        )
        self.assertEqual({ctx.user_id for ctx, _ in self.factory_calls}, {"user-1", "user-2"})
        self.assertEqual(self.llm.invoke.call_count, 2)

    async def test_real_binding_constructor_shares_step_allocator(self):
        bindings = EngineBindings.for_request(
            oe_url="https://oe.invalid", context=self.context,
            schemas=[self.tool.schema()], llm_id="configured-model", model_name="configured-provider",
        )
        self.assertEqual(bindings.llm.execution_id, "exec-1")
        self.assertEqual(bindings.tools.execution_id, "exec-1")
        self.assertIs(bindings.llm.operational_steps, bindings.tools.operational_steps)
        self.assertEqual(bindings.llm._serialize_bound_tools(), [self.tool.schema()])
        other = EngineBindings.for_request(
            oe_url="https://oe.invalid", context=self.context.model_copy(update={"execution_id": "exec-2"}),
            schemas=[], llm_id="configured-model", model_name="configured-provider",
        )
        self.assertIsNot(other.llm.operational_steps, bindings.llm.operational_steps)


if __name__ == "__main__":
    unittest.main()
