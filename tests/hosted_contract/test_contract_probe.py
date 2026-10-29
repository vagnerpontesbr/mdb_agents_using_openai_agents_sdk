"""Probe validation with doubled OE; live enforcement is recorded separately."""

import unittest
from unittest.mock import create_autospec

from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ActivityContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import (
    WorkflowIdentity, TenantScope, WORKFLOW_ERROR_CODE_NONDETERMINISTIC,
    WORKFLOW_ERROR_CODE_STALE_FENCE, WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN,
)
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.workflow import WorkflowClient, WorkflowClientError, attempt_context_scope
from agent_engine_runner_shared.workflow.activity import completed_outcome
from agent_engine_runner_shared.workflow.client import ActivityReplay
from openai_engine_adapter.adapter import UnsupportedContract
from openai_engine_adapter.contract_probe import probe_activity_contract


class ContractProbeTests(unittest.TestCase):
    def setUp(self):
        identity = WorkflowIdentity(tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="workspace"),
                                    session_id="session", execution_id="exec")
        self.attempt = AttemptContext(workflow_identity=identity, attempt_id="new", fencing_token=2, replay_mode=True)
        activity = ActivityContext(workflow_identity=identity, attempt_id="old", fencing_token=1, activity_id="control")
        self.replay = ActivityReplay(completed_outcome(activity, {"attempt_id": "old", "fencing_token": 1}))
        self.client = create_autospec(WorkflowClient, instance=True)

    def run_probe(self):
        with attempt_context_scope(self.attempt):
            return probe_activity_contract(self.client, self.attempt, 1)

    def test_exact_rejections_and_original_fence_are_required(self):
        self.client.start_activity.side_effect = [self.replay] + [
            WorkflowClientError(WORKFLOW_ERROR_CODE_NONDETERMINISTIC, "changed") for _ in range(3)
        ] + [WorkflowClientError(WORKFLOW_ERROR_CODE_STALE_FENCE, "old")]
        self.assertEqual(self.run_probe(), {"changed_arguments": "rejected", "changed_tool_call_id": "rejected",
                                          "changed_tool_name": "rejected", "stale_attempt": "rejected"})
        first = self.client.start_activity.call_args_list[0].args[0]
        last = self.client.start_activity.call_args_list[-1].args[0]
        self.assertEqual(first.position, last.position)
        self.assertEqual(first.semantic_input, last.semantic_input)
        self.assertEqual((last.attempt_id, last.fencing_token), ("old", 1))
        self.client.report_outcome.assert_not_called()

    def test_unexpected_acceptance_fails_without_reporting_an_outcome(self):
        self.client.start_activity.side_effect = [self.replay, self.replay]
        with self.assertRaises(UnsupportedContract):
            self.run_probe()
        self.assertEqual(self.client.start_activity.call_count, 2)
        self.client.report_outcome.assert_not_called()

    def test_unknown_error_is_not_labelled_as_successful_control(self):
        self.client.start_activity.side_effect = [self.replay,
            WorkflowClientError(WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN, "lost response")]
        with self.assertRaises(WorkflowClientError) as error:
            self.run_probe()
        self.assertEqual(error.exception.code, WORKFLOW_ERROR_CODE_OUTCOME_UNKNOWN)
        self.assertEqual(self.client.start_activity.call_count, 2)

    def test_first_attempt_does_not_fabricate_a_stale_lease(self):
        self.attempt.replay_mode = False
        self.client.start_activity.side_effect = [self.replay] + [
            WorkflowClientError(WORKFLOW_ERROR_CODE_NONDETERMINISTIC, "changed") for _ in range(3)]
        self.assertEqual(self.run_probe()["stale_attempt"], "awaiting_resume")
        self.assertEqual(self.client.start_activity.call_count, 4)
