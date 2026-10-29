"""Real AER stream parser and Engine activity/settlement; doubled OE transport."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_engine_sdk.models import AgentInput, AgentOutput, RequestContext
from agent_engine_runner_shared.models import InterruptResult
from agent_engine_runner_shared.server.aer import AERServer
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ActivityContext
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.workflow import attempt_context_scope
from agent_engine_runner_shared.workflow.activity import completed_outcome, suspended_outcome
from agent_engine_runner_shared.workflow.client import ActivityDispatch, ActivityReplay

from openai_engine_adapter.review import ReviewAction
from openai_engine_adapter.review_execution import ReviewExecutionAgent
from openai_engine_adapter.adapter import UnsupportedContract


class ReviewExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ctx = RequestContext(execution_id="exec", session_id="session", workspace_id="workspace", user_id="user")
        identity = WorkflowIdentity(tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="workspace"),
                                    session_id="session", execution_id="exec")
        self.attempt = AttemptContext(workflow_identity=identity, attempt_id="attempt-1", fencing_token=1)
        self.activity = ActivityContext(workflow_identity=identity, attempt_id="attempt-1", fencing_token=1, activity_id="review-1")
        self.result = '{"invoice_id":"demo-1","amount_minor":7990}'
        self.read = SimpleNamespace(execute=AsyncMock(return_value=AgentOutput(response={"output": self.result})))
        self.agent = ReviewExecutionAgent(self.read, lambda result: ReviewAction(
            tool_name="release_invoice", tool_call_id="release-1", arguments=json.loads(result),
        ))
        self.client = MagicMock()
        self.client.__enter__.return_value = self.client
        self.settlement = MagicMock()
        self.settlement.__aenter__ = AsyncMock(return_value=self.settlement)
        self.settlement.__aexit__ = AsyncMock(return_value=False)
        self.settlement.finalize_step = AsyncMock(return_value=[])
        self.settlement.complete_execution = AsyncMock()
        self.patches = [
            patch("openai_engine_adapter.review_execution.get_current_oe_url", return_value="https://oe.invalid"),
            patch("openai_engine_adapter.review_execution.WorkflowClient", return_value=self.client),
            patch("openai_engine_adapter.review_execution.AsyncWorkflowClient", return_value=self.settlement),
            patch("agent_engine_runner_shared.workflow.settlement.get_current_oe_url", return_value="https://oe.invalid"),
            patch("agent_engine_runner_shared.workflow.settlement.AsyncWorkflowClient", return_value=self.settlement),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def parse(self, ctx=None):
        return await AERServer._execute_via_agent_stream(
            SimpleNamespace(), self.agent, ctx or self.ctx, AgentInput(payload={"message": "Read demo-1"}),
            "https://oe.invalid", "exec",
        )

    async def test_aer_receives_suspension_only_after_engine_records_wait(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        async def finalize(command):
            self.assertEqual(len(command.suspensions), 1)
            pause = command.suspensions[0]
            self.assertEqual(pause.suspension.reason, "agent_interrupt")
            return [SimpleNamespace(position=pause.position, outcome=suspended_outcome(
                self.activity, reason="agent_interrupt", context={}))]
        self.settlement.finalize_step.side_effect = finalize
        with attempt_context_scope(self.attempt):
            outcome = await self.parse()
        self.assertIsInstance(outcome, InterruptResult)
        self.assertEqual(outcome.metadata, {})
        self.assertEqual(outcome.interrupts[0].value["action"]["arguments"]["invoice_id"], "demo-1")
        self.assertEqual(outcome.interrupts[0].id, "review-1")
        self.assertEqual(outcome.resume_schema["properties"]["resume_map"]["required"], ["review-1"])
        self.client.report_outcome.assert_not_called()
        self.settlement.finalize_step.assert_called_once()

    async def test_resumed_decision_settles_same_state_before_releasing_result(self):
        for decision in ("approve", "reject"):
            with self.subTest(decision=decision):
                self.client.reset_mock()
                self.settlement.reset_mock()
                self.client.start_activity.return_value = ActivityReplay(completed_outcome(self.activity, {"decision": decision}))
                fresh = AttemptContext(workflow_identity=self.attempt.workflow_identity, attempt_id="attempt-2", fencing_token=2, replay_mode=True)
                with attempt_context_scope(fresh):
                    result = await self.parse(self.ctx.model_copy(update={"resume": True, "resume_data": {"review-1": {"decision": "approve"}}}))
                expected = self.result if decision == "approve" else '{"status":"rejected","tool_call_id":"release-1"}'
                self.assertEqual(result.content, expected)
                self.client.report_outcome.assert_not_called()
                final = self.settlement.finalize_step.call_args.args[0]
                complete = self.settlement.complete_execution.call_args.args[0]
                self.assertEqual(final.state, complete.state)
                self.assertEqual(complete.fencing_token, 2)

    async def test_failed_suspension_recording_does_not_emit_suspended(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        self.settlement.finalize_step.side_effect = TimeoutError("Synthetic delivery uncertainty")
        with attempt_context_scope(self.attempt), self.assertRaises(TimeoutError):
            await self.parse()
        self.settlement.complete_execution.assert_not_called()

    async def test_answer_resolved_during_finalization_settles_without_obsolete_wait(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        async def finalize(command):
            if not command.suspensions:
                return []
            return [SimpleNamespace(position=command.suspensions[0].position,
                outcome=completed_outcome(self.activity, {"decision": "reject"}))]
        self.settlement.finalize_step.side_effect = finalize
        with attempt_context_scope(self.attempt):
            result = await self.parse()
        self.assertEqual(result.content, '{"status":"rejected","tool_call_id":"release-1"}')
        self.settlement.complete_execution.assert_called_once()
        self.client.report_outcome.assert_not_called()

    async def test_empty_frontier_fails_without_publishing_wait_or_result(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        with attempt_context_scope(self.attempt), self.assertRaises(UnsupportedContract):
            await self.parse()
        self.client.report_outcome.assert_not_called()
        self.settlement.complete_execution.assert_not_called()

    async def test_failed_completion_does_not_emit_success(self):
        self.client.start_activity.return_value = ActivityReplay(completed_outcome(self.activity, {"decision": "approve"}))
        self.settlement.complete_execution.side_effect = TimeoutError("Synthetic completion uncertainty")
        with attempt_context_scope(self.attempt), self.assertRaises(TimeoutError):
            await self.parse()

    async def test_unbound_or_untrusted_resume_never_starts_read(self):
        with self.assertRaises(UnsupportedContract):
            await self.parse()
        with attempt_context_scope(self.attempt), self.assertRaises(UnsupportedContract):
            await self.parse(self.ctx.model_copy(update={"resume": True, "resume_data": {"decision": "approve"}}))
        self.read.execute.assert_not_called()

    async def test_expired_approval_never_releases_invoice(self):
        self.agent.ttl_seconds = 60
        self.client.start_activity.side_effect = [
            ActivityReplay(completed_outcome(self.activity, {"issued_at": 1000.0, "expires_at": 1060.0})),
            ActivityReplay(completed_outcome(self.activity, {"decision": "approve"})),
        ]
        with attempt_context_scope(self.attempt), patch("openai_engine_adapter.review_deadline.time.time", return_value=1060.0):
            result = await self.parse()
        self.assertEqual(result.content, '{"status":"expired","tool_call_id":"release-1"}')
        self.client.report_outcome.assert_not_called()
        self.settlement.complete_execution.assert_called_once()

    async def test_approval_before_deadline_releases_original_result(self):
        self.agent.ttl_seconds = 60
        self.client.start_activity.side_effect = [
            ActivityReplay(completed_outcome(self.activity, {"issued_at": 1000.0, "expires_at": 1060.0})),
            ActivityReplay(completed_outcome(self.activity, {"decision": "approve"})),
        ]
        with attempt_context_scope(self.attempt), patch("openai_engine_adapter.review_deadline.time.time", return_value=1059.0):
            result = await self.parse()
        self.assertEqual(result.content, self.result)
        self.client.report_outcome.assert_not_called()
