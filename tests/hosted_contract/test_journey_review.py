"""Journey native review ordering; real AER parser, doubled Engine transport."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_engine_sdk.models import AgentInput, AgentOutput, RequestContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.workflow import attempt_context_scope
from agent_engine_runner_shared.server.aer import AERServer

from openai_engine_adapter.journey import JourneyExecution
from openai_engine_adapter.journey_domain import JourneyResult, offer_plan, simulate_change
from openai_engine_adapter.review import ReviewDecision, ReviewInterrupt
from openai_engine_adapter.adapter import UnsupportedContract


class JourneyReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ctx = RequestContext(user_id="user", execution_id="exec", session_id="session", workspace_id="ws")
        self.attempt = AttemptContext(workflow_identity=WorkflowIdentity(
            tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="ws"),
            execution_id="exec", session_id="session"), attempt_id="attempt", fencing_token=1)
        proposal = offer_plan("user", "fiber-500", True)
        result = JourneyResult(status="completed", text=proposal.text, specialists=["sales"], results=[proposal])
        self.read = SimpleNamespace(execute=AsyncMock(return_value=AgentOutput(response={"output": result.model_dump_json()})))
        self.tools = MagicMock()
        self.tools.execute_tool.return_value = simulate_change("user", "fiber-500", 8990, proposal.reference).model_dump_json()
        self.agent = JourneyExecution(SimpleNamespace(_runtime=None), lambda *args: SimpleNamespace(tools=self.tools))
        self.deadline = SimpleNamespace(expired=lambda: False)
        self.settle = AsyncMock()
        patches = [
            patch("openai_engine_adapter.journey.JourneyAgent", return_value=self.read),
            patch("openai_engine_adapter.journey.get_current_oe_url", return_value="https://oe.invalid"),
            patch("openai_engine_adapter.journey.WorkflowClient"),
            patch("openai_engine_adapter.journey.record_deadline", return_value=self.deadline),
            patch("openai_engine_adapter.journey.settle_execution", self.settle),
        ]
        for p in patches:
            p.start(); self.addCleanup(p.stop)

    async def run_journey(self, ctx=None):
        with attempt_context_scope(self.attempt):
            return await AERServer._execute_via_agent_stream(SimpleNamespace(), self.agent,
                ctx or self.ctx, AgentInput(payload={"message": "Simulate fiber-500"}), "https://oe.invalid", "exec")

    async def test_only_native_approval_releases_exact_simulation(self):
        with patch("openai_engine_adapter.journey.request_review", return_value=ReviewDecision(decision="approve")) as review:
            output = await self.run_journey()
        action = review.call_args.kwargs["action"]
        self.tools.execute_tool.assert_called_once_with("telco_simulate_plan_change", action.arguments,
            tool_call_id="journey-plan-change", is_local=False, on_unknown_outcome="fail")
        self.assertEqual(json.loads(output.content)["results"][-1]["kind"], "simulation")
        self.settle.assert_awaited_once()

    async def test_localized_review_retains_exact_action_and_renders_receipt(self):
        from openai_engine_adapter.journey_locale import render, price
        for locale in ("pt-BR", "es-ES"):
            original = self.read.execute.return_value
            result = JourneyResult.model_validate_json(original.response["output"])
            self.read.execute.return_value = AgentOutput(response={"output": result.model_copy(
                update={"locale": locale}).model_dump_json()})
            self.tools.reset_mock()
            with patch("openai_engine_adapter.journey.request_review", return_value=ReviewDecision(decision="approve")) as review:
                output = await self.run_journey()
            action = review.call_args.kwargs["action"]
            self.assertEqual(set(action.arguments), {"plan_id", "monthly_minor", "proposal_id"})
            self.tools.execute_tool.assert_called_once_with("telco_simulate_plan_change", action.arguments,
                tool_call_id="journey-plan-change", is_local=False, on_unknown_outcome="fail")
            presented = json.loads(output.content)
            self.assertEqual(presented["locale"], locale)
            self.assertEqual(presented["text"], render("simulation.v1", locale,
                plan="fiber-500", price=price(8990, locale)))

    async def test_rejection_and_expiry_never_call_simulation(self):
        for decision, expired, expected in (("reject", False, "rejected"), ("approve", True, "expired")):
            self.deadline.expired = lambda: expired
            with patch("openai_engine_adapter.journey.request_review", return_value=ReviewDecision(decision=decision)):
                output = await self.run_journey()
            self.assertEqual(json.loads(output.content)["status"], expected)
        self.tools.execute_tool.assert_not_called()

    async def test_failed_native_review_never_calls_simulation_or_completes(self):
        with patch("openai_engine_adapter.journey.request_review", side_effect=TimeoutError("uncertain")):
            with self.assertRaises(TimeoutError):
                await self.run_journey()
        self.tools.execute_tool.assert_not_called()
        self.settle.assert_not_awaited()

    async def test_failed_finalization_does_not_publish_suspended_or_success(self):
        with patch("openai_engine_adapter.journey.request_review", side_effect=ReviewInterrupt({})), \
             patch("openai_engine_adapter.journey.finalize_review_interrupt", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                await self.run_journey()
        self.tools.execute_tool.assert_not_called()
        self.settle.assert_not_awaited()

    async def test_wrong_subject_receipt_is_not_success(self):
        p = offer_plan("other", "fiber-500", True)
        self.tools.execute_tool.return_value = simulate_change("other", "fiber-500", 8990, p.reference).model_dump_json()
        with patch("openai_engine_adapter.journey.request_review", return_value=ReviewDecision(decision="approve")):
            with self.assertRaises(UnsupportedContract):
                await self.run_journey()
        self.settle.assert_not_awaited()

    async def test_resume_without_engine_replay_rejected_before_read(self):
        with self.assertRaises(UnsupportedContract):
            await self.run_journey(self.ctx.model_copy(update={"resume": True, "resume_data": {"x": "approve"}}))
        self.read.execute.assert_not_called()
