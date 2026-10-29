"""Engine activity-backed clock sampling with explicit transport doubles."""
import unittest
from unittest.mock import create_autospec, patch
from agent_engine_sdk.models import RequestContext
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ActivityContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.workflow import WorkflowClient, attempt_context_scope
from agent_engine_runner_shared.workflow.activity import completed_outcome
from agent_engine_runner_shared.workflow.client import ActivityDispatch, ActivityReplay
from openai_engine_adapter.review import ReviewAction
from openai_engine_adapter.review_deadline import record_deadline

class DeadlineTests(unittest.TestCase):
    def test_restart_replays_deadline_instead_of_extending_it(self):
        identity = WorkflowIdentity(tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="workspace"),
                                    execution_id="exec", session_id="session")
        attempt = AttemptContext(workflow_identity=identity, attempt_id="one", fencing_token=1)
        activity = ActivityContext(workflow_identity=identity, attempt_id="one", fencing_token=1, activity_id="clock")
        client = create_autospec(WorkflowClient, instance=True)
        client.start_activity.return_value = ActivityDispatch(activity)
        args = dict(client=client, context=RequestContext(user_id="user"),
                    action=ReviewAction(tool_name="read", tool_call_id="call", arguments={}), ttl_seconds=60, ordinal=1)
        with attempt_context_scope(attempt), patch("openai_engine_adapter.review_deadline.time.time", return_value=1000):
            deadline = record_deadline(**args)
        client.report_outcome.assert_called_once()
        client.start_activity.return_value = ActivityReplay(completed_outcome(activity, deadline.model_dump()))
        client.reset_mock()
        attempt.attempt_id = "two"
        attempt.fencing_token = 2
        attempt.replay_mode = True
        with attempt_context_scope(attempt), patch("openai_engine_adapter.review_deadline.time.time", side_effect=AssertionError("must not renew")):
            restored = record_deadline(**args)
        self.assertEqual(restored, deadline)
        self.assertEqual(restored.expires_at, 1060)
        client.report_outcome.assert_not_called()
