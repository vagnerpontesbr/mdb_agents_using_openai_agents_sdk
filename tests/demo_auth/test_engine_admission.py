import copy
import unittest
from unittest.mock import Mock

from compatibility.demo_auth.auth import AccessDenied, Principal
from compatibility.demo_auth.engine import EngineReview, ORG, PROJECT, WORKSPACE, ReviewConflict

EXECUTION = "11111111-1111-1111-1111-111111111111"


class Transport:
    def __init__(self):
        self.calls = []
        self.execution = {"execution_id": EXECUTION, "org_id": ORG, "project_id": PROJECT,
                          "workspace_id": WORKSPACE, "user_id": "requester", "status": "suspended",
                          "session_id": "demo-invoice-synthetic", "suspend_generation": 1,
                          "suspend_context": {"interrupts": [{"id": "interrupt", "value": {
                              "requesting_user_id": "requester", "contract": "openai-engine-review-v1",
                              "allowed_decisions": ["approve", "reject"], "action": {
                                  "tool_name": "release_synthetic_recall", "tool_call_id": "release-demo-1",
                                  "arguments": {"invoice_id": "demo-1", "amount_minor": 7990,
                                                "currency": "USD", "synthetic": True,
                                                "model_reported_marker": "not_found"}}}}]}}

    def get_execution(self, execution):
        return copy.deepcopy(self.execution)

    def invoke(self, user, session, **kwargs):
        import json
        self.calls.append((user, session, kwargs))
        self.execution["status"] = "completed"
        return {"execution_id": EXECUTION, "session_id": session,
                "response": json.dumps(self.execution["suspend_context"]["interrupts"][0]["value"]["action"]["arguments"])}


class EngineAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.transport = Transport()
        self.sessions = Mock()
        principals = {"owner-token": Principal("requester", "owner@example.test", "user"),
                      "other-token": Principal("other", "admin@example.test", "admin")}
        self.sessions.principal.side_effect = lambda token: principals[token]
        self.gateway = EngineReview(self.sessions, self.transport)

    def test_other_admin_denied_before_any_resume_and_pending_preserved(self):
        pending = self.gateway.pending("owner-token", EXECUTION)
        with self.assertRaises(AccessDenied):
            self.gateway.decide("other-token", execution_id=EXECUTION,
                                action_digest=pending["action_digest"], decision="approve")
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.transport.execution["status"], "suspended")

    def test_changed_action_digest_denied_then_owner_succeeds(self):
        pending = self.gateway.pending("owner-token", EXECUTION)
        with self.assertRaises(ReviewConflict):
            self.gateway.decide("owner-token", execution_id=EXECUTION, action_digest="tampered", decision="approve")
        self.assertEqual(self.transport.calls, [])
        result = self.gateway.decide("owner-token", execution_id=EXECUTION,
                                    action_digest=pending["action_digest"], decision="approve")
        self.assertEqual(result["result"]["invoice_id"], "demo-1")
        self.assertEqual(len(self.transport.calls), 1)
        with self.assertRaises(ReviewConflict):
            self.gateway.decide("owner-token", execution_id=EXECUTION,
                                action_digest=pending["action_digest"], decision="approve")
        self.assertEqual(len(self.transport.calls), 1)

    def test_cross_workspace_or_missing_generation_cannot_pass(self):
        for key, invalid in (("workspace_id", "other"), ("suspend_generation", None)):
            original = self.transport.execution[key]
            self.transport.execution[key] = invalid
            with self.assertRaises(ReviewConflict):
                self.gateway.pending("owner-token", EXECUTION)
            self.transport.execution[key] = original
        self.assertEqual(self.transport.calls, [])

    def test_session_revoked_during_engine_read_prevents_resume(self):
        pending = self.gateway.pending("owner-token", EXECUTION)
        self.sessions.principal.side_effect = [Principal("requester", "owner@example.test", "user"), AccessDenied()]
        with self.assertRaises(AccessDenied):
            self.gateway.decide("owner-token", execution_id=EXECUTION,
                                action_digest=pending["action_digest"], decision="approve")
        self.assertEqual(self.transport.calls, [])


if __name__ == "__main__":
    unittest.main()
