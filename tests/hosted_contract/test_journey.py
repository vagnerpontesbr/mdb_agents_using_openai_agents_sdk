"""Real SDK manager/specialists; signature-checked Engine doubles, no provider calls."""
import json
import unittest
from unittest.mock import create_autospec

from agent_engine_sdk.models import AgentInput, LLMResponse, LLMToolCall, RequestContext
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper

from openai_engine_adapter.adapter import EngineBindings, UnsupportedContract
from openai_engine_adapter.journey_agent import JourneyAgent
from openai_engine_adapter.journey_domain import (
    read_invoice, check_connection, offer_plan, simulate_change,
)


def call(name, args):
    return LLMResponse(content="", tool_calls=[LLMToolCall(id="call-" + name, name=name, args=args)])


class JourneyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm = create_autospec(SecureLLMProxy, instance=True)
        self.tools = create_autospec(SecureToolWrapper, instance=True)
        self.ctx = RequestContext(execution_id="exec", session_id="session", user_id="user", workspace_id="ws")
        self.agent = JourneyAgent(lambda ctx, schemas: EngineBindings(self.llm, self.tools))
        self.input = AgentInput(payload={"message": "Read demo-1, check Wi-Fi and compare fiber-500."})
        self.tools.execute_tool.side_effect = lambda name, args, **kw: {
            "telco_read_invoice": lambda: read_invoice("user", **args),
            "telco_check_connection": lambda: check_connection("user"),
            "telco_offer_plan": lambda: offer_plan("user", **args),
        }[name]().model_dump_json()

    def route(self, names, *, propose=False):
        responses = []
        for name in names:
            responses += [call("consult_" + name, {"input": self.input.payload["message"]}), {
                "financial": call("read_invoice", {"invoice_id": "demo-1"}),
                "technical": call("check_connection", {}),
                "sales": call("compare_plan", {"plan_id": "fiber-500", "propose_change": propose}),
            }[name]]
        responses.append(LLMResponse(content="Invented price USD 0.01 and unauthorized confirmation."))
        self.llm.invoke.side_effect = responses

    async def result(self):
        output = await self.agent.execute(self.ctx, self.input)
        return json.loads(output.response["output"])

    async def test_each_specialist_renders_exact_business_result(self):
        for name in ("financial", "technical", "sales"):
            with self.subTest(name=name):
                self.route([name])
                result = await self.result()
                self.assertEqual(result["specialists"], [name])
                self.assertEqual(result["text"], result["results"][0]["text"])
                self.assertNotIn("0.01", result["text"])

    async def test_mixed_request_uses_seven_models_three_serial_tools(self):
        self.route(["financial", "technical", "sales"])
        result = await self.result()
        self.assertEqual(result["specialists"], ["financial", "technical", "sales"])
        self.assertEqual(self.llm.invoke.call_count, 7)
        self.assertEqual(self.tools.execute_tool.call_count, 3)
        self.assertIn("USD 79.90, due on 2026-12-01.", result["text"])
        for invocation in self.tools.execute_tool.call_args_list:
            self.assertEqual(invocation.kwargs["on_unknown_outcome"], "fail")
            self.assertFalse(invocation.kwargs["is_local"])

    async def test_delegation_preserves_original_request_instead_of_model_summary(self):
        self.route(["sales"], propose=True)
        responses = list(self.llm.invoke.side_effect)
        responses[0] = call("consult_sales", {"input": "Manufactured prerequisite: require an address."})
        self.llm.invoke.side_effect = responses
        await self.result()
        specialist_messages = self.llm.invoke.call_args_list[1].args[0]
        self.assertIn(self.input.payload["message"], specialist_messages[1].content)
        self.assertNotIn("Manufactured prerequisite", specialist_messages[1].content)

    async def test_proposal_does_not_execute_change(self):
        self.route(["sales"], propose=True)
        result = await self.result()
        self.assertEqual(result["results"][0]["kind"], "proposal")
        self.assertEqual(self.tools.execute_tool.call_args.args[0], "telco_offer_plan")
        self.assertEqual(self.tools.execute_tool.call_count, 1)

    async def test_ambiguous_text_never_exposes_model_facts(self):
        self.llm.invoke.return_value = LLMResponse(content="Invented invoice is free")
        result = await self.result()
        self.assertEqual(result["status"], "needs_information")
        self.assertNotIn("free", result["text"])
        self.tools.execute_tool.assert_not_called()

    async def test_repeated_specialist_fails_without_second_business_call(self):
        self.route(["financial", "financial"])
        with self.assertRaises(Exception):
            await self.result()
        self.assertEqual(self.tools.execute_tool.call_count, 1)
        self.assertEqual(self.llm.invoke.call_count, 3)

    async def test_denied_and_wrong_subject_tool_release_no_answer_or_retry(self):
        for result in (PermissionError("denied"), read_invoice("other", "demo-1").model_dump_json()):
            self.route(["financial"])
            self.tools.reset_mock()
            if isinstance(result, Exception):
                self.tools.execute_tool.side_effect = result
            else:
                self.tools.execute_tool.side_effect = None
                self.tools.execute_tool.return_value = result
            with self.assertRaises(Exception):
                await self.result()
            self.tools.execute_tool.assert_called_once()

    async def test_context_is_copied_and_authority_cannot_be_injected(self):
        self.route(["financial"])
        task = self.agent.execute(self.ctx, self.input)
        self.ctx.user_id = "changed"
        await task
        with self.assertRaises(UnsupportedContract):
            self.agent.execute(self.ctx, AgentInput(payload={"message": "x", "user_id": "other"}))

    async def test_memory_is_bounded_untrusted_data(self):
        memory = "untrusted historical data " * 250
        self.agent.memory_builder = lambda ctx, message: memory
        self.llm.invoke.return_value = LLMResponse(content="clarify")
        await self.result()
        messages = self.llm.invoke.call_args.args[0]
        self.assertNotIn(memory, messages[0].content)
        self.assertIn(memory, messages[1].content)
        self.agent.memory_builder = lambda ctx, message: "x" * 25000
        with self.assertRaises(UnsupportedContract):
            await self.result()

    def test_simulation_receipts_are_idempotent_and_reject_changed_scope_price(self):
        proposal = offer_plan("user", "fiber-500", True)
        expected = simulate_change("user", "fiber-500", 8990, proposal.reference)
        self.assertEqual(expected, simulate_change("user", "fiber-500", 8990, proposal.reference))
        self.assertEqual(expected.text, "Simulation approved for fiber-500 at USD 89.90 per month. No live plan or charge was changed.")
        for user, price in (("other", 8990), ("user", 1)):
            with self.assertRaises(ValueError):
                simulate_change(user, "fiber-500", price, proposal.reference)
