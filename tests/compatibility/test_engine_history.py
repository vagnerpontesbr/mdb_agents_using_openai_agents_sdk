"""History availability is not inferred from a successful HTTP envelope."""
import unittest
from scripts.check_engine_history import assess


class HistoryProbeTests(unittest.TestCase):
    def response(self, **changes):
        return {"history_status": "ready", "latest_status": "completed",
                "outcome_supported": True,
                "messages": [{"session_id": "s", "role": "user"}], **changes}

    def test_observation_never_claims_sdk_compatibility(self):
        result = assess(self.response(), session="s")
        self.assertEqual(result["status"], "observed")
        self.assertIs(result["sdk_restoration_proven"], False)

    def test_live_empty_completed_envelope_is_blocked(self):
        result = assess(self.response(messages=[]), session="s")
        self.assertEqual(result["reason"], "completed_session_has_no_history")

    def test_warming_and_active_sessions_are_not_authoritative(self):
        for changes in ({"history_status": "warming"}, {"latest_status": "running"}):
            with self.subTest(changes=changes):
                self.assertEqual(assess(self.response(**changes), session="s")["status"], "blocked")

    def test_missing_outcome_support_is_not_assumed(self):
        response = self.response()
        del response["outcome_supported"]
        self.assertEqual(assess(response, session="s")["reason"], "outcome_classification_unavailable")

    def test_wrong_scope_privileged_roles_and_cancelled_messages_fail(self):
        for message in ({"session_id": "other", "role": "user"},
                        {"session_id": "s", "role": "system"},
                        {"session_id": "s", "role": "user", "outcome": "cancelled"}):
            with self.subTest(message=message):
                self.assertEqual(assess(self.response(messages=[message]), session="s")["status"], "blocked")

    def test_malformed_and_oversized_responses_fail(self):
        for response in (None, self.response(messages={}), self.response(messages=[{}] * 101)):
            with self.subTest(response_type=type(response).__name__):
                self.assertEqual(assess(response, session="s")["status"], "blocked")
