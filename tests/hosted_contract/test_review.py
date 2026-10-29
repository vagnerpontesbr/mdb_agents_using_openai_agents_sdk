"""Actual Engine activity helper with doubled OE responses, not live replay."""

import unittest
from unittest.mock import create_autospec

from pydantic import ValidationError
from agent_engine_sdk.models import RequestContext
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import (
    ActivityContext, UNKNOWN_OUTCOME_POLICY_FAIL,
)
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import (
    WorkflowIdentity, TenantScope, WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN,
    WORKFLOW_ERROR_CODE_CONFLICT, WORKFLOW_ERROR_CODE_STALE_FENCE,
)
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.workflow import (
    DurableActivityDeniedError, WorkflowClient,
    WorkflowClientError, attempt_context_scope,
)
from agent_engine_runner_shared.workflow.activity import completed_outcome, denied_outcome, value_to_json
from agent_engine_runner_shared.workflow.client import ActivityDispatch, ActivityReplay

from openai_engine_adapter.review import ReviewAction, ReviewInterrupt, request_review
from agent_engine_runner_shared.workflow.context import interrupted_activities, current_step_ordinal
from openai_engine_adapter.adapter import UnsupportedContract


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.ctx = RequestContext(execution_id="exec", session_id="session", workspace_id="workspace", user_id="user")
        self.identity = WorkflowIdentity(
            tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="workspace"),
            session_id="session", execution_id="exec",
        )
        self.attempt = AttemptContext(workflow_identity=self.identity, attempt_id="attempt-1", fencing_token=1)
        self.activity = ActivityContext(workflow_identity=self.identity, attempt_id="attempt-1",
                                        fencing_token=1, activity_id="review-1")
        self.action = ReviewAction(tool_name="lookup_invoice", tool_call_id="call-1", arguments={"invoice_id": "demo-1"})
        self.client = create_autospec(WorkflowClient, instance=True)

    def run_review(self):
        return request_review(client=self.client, context=self.ctx, action=self.action, activity_ordinal=2)

    def test_first_attempt_records_wait_and_never_returns_approval(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        with attempt_context_scope(self.attempt):
            with self.assertRaises(ReviewInterrupt):
                self.run_review()
            pending = interrupted_activities(current_step_ordinal())
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].control_flow.value["allowed_decisions"], ["approve", "reject"])
        command = self.client.start_activity.call_args.args[0]
        self.assertEqual(command.workflow_identity, self.identity)
        self.assertEqual(command.position.activity_ordinal, 2)
        self.assertEqual(command.on_unknown_outcome, UNKNOWN_OUTCOME_POLICY_FAIL)
        semantic = value_to_json(command.semantic_input)
        self.assertEqual(semantic["action"], self.action.model_dump())
        self.assertEqual(semantic["requesting_user_id"], "user")
        self.client.report_outcome.assert_not_called()

    def test_fresh_attempt_consumes_recorded_decision_without_resuspending(self):
        for decision in ("approve", "reject"):
            with self.subTest(decision=decision):
                self.client.reset_mock()
                self.client.start_activity.return_value = ActivityReplay(completed_outcome(self.activity, {"decision": decision}))
                fresh = AttemptContext(workflow_identity=self.identity, attempt_id="attempt-2", fencing_token=2, replay_mode=True)
                with attempt_context_scope(fresh):
                    result = self.run_review()
                self.assertEqual(result.decision, decision)
                self.client.start_activity.assert_called_once()
                self.client.report_outcome.assert_not_called()

    def test_recorded_denial_is_not_approval(self):
        self.client.start_activity.return_value = ActivityReplay(denied_outcome(self.activity, "Synthetic denial"))
        with attempt_context_scope(self.attempt), self.assertRaises(DurableActivityDeniedError):
            self.run_review()
        self.client.report_outcome.assert_not_called()

    def test_unknown_activity_start_is_not_retried_or_relabelled(self):
        self.client.start_activity.return_value = ActivityDispatch(self.activity)
        self.client.start_activity.side_effect = WorkflowClientError(WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN, "Synthetic lost response")
        with attempt_context_scope(self.attempt), self.assertRaises(WorkflowClientError) as error:
            self.run_review()
        self.assertEqual(error.exception.code, WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN)
        self.client.start_activity.assert_called_once()
        self.client.report_outcome.assert_not_called()

    def test_missing_attempt_and_mismatched_identity_fail_before_transport(self):
        with self.assertRaises(UnsupportedContract):
            self.run_review()
        for field in ("execution_id", "session_id", "workspace_id"):
            with self.subTest(field=field), attempt_context_scope(self.attempt), self.assertRaises(UnsupportedContract):
                request_review(client=self.client, context=self.ctx.model_copy(update={field: "other"}),
                               action=self.action, activity_ordinal=2)
        self.client.start_activity.assert_not_called()

    def test_malformed_recorded_decision_is_not_accepted(self):
        for answer in ({"decision": "allow"}, {"decision": "approve", "arguments": {}}, "approve"):
            with self.subTest(answer=answer):
                self.client.start_activity.return_value = ActivityReplay(completed_outcome(self.activity, answer))
                with attempt_context_scope(self.attempt), self.assertRaises(ValidationError):
                    self.run_review()
        self.client.report_outcome.assert_not_called()

    def test_engine_action_conflict_and_stale_fence_propagate_without_fallback(self):
        # Doubled OE rejection: validates adapter propagation, not server fencing.
        for code in (WORKFLOW_ERROR_CODE_CONFLICT, WORKFLOW_ERROR_CODE_STALE_FENCE):
            with self.subTest(code=code):
                self.client.reset_mock()
                self.client.start_activity.side_effect = WorkflowClientError(code, "Synthetic rejected attempt")
                with attempt_context_scope(self.attempt), self.assertRaises(WorkflowClientError) as error:
                    self.run_review()
                self.assertEqual(error.exception.code, code)
                self.client.start_activity.assert_called_once()
                self.client.report_outcome.assert_not_called()
                command = self.client.start_activity.call_args.args[0]
                self.assertEqual(command.attempt_id, self.attempt.attempt_id)
                self.assertEqual(command.fencing_token, self.attempt.fencing_token)

    def test_action_changes_remain_visible_to_engine_semantic_comparison(self):
        self.client.start_activity.return_value = ActivityReplay(
            completed_outcome(self.activity, {"decision": "reject"}))
        variants = [self.action,
            self.action.model_copy(update={"arguments": {"invoice_id": "other"}}),
            self.action.model_copy(update={"tool_call_id": "different-call"}),
            self.action.model_copy(update={"tool_name": "different-tool"})]
        semantics = []
        for action in variants:
            with attempt_context_scope(self.attempt):
                request_review(client=self.client, context=self.ctx, action=action, activity_ordinal=2)
            command = self.client.start_activity.call_args.args[0]
            self.assertEqual(command.position.activity_ordinal, 2)
            semantics.append(command.semantic_input.SerializeToString(deterministic=True))
        self.assertEqual(len(set(semantics)), len(variants))
        self.client.report_outcome.assert_not_called()
