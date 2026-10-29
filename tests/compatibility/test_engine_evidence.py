"""Failure evidence tests with an offline SDK double, not provider acceptance."""

import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from scripts.check_compatibility import run_live


class EngineEvidenceTests(unittest.TestCase):
    def run_probe(self, failure=None, leaked=False, acknowledged=True):
        sdk = MagicMock()
        memory = sdk.Memory.return_value.__enter__.return_value
        own, other = MagicMock(), MagicMock()
        memory.bind.side_effect = [own, other]
        own.record_turn.return_value = SimpleNamespace(acknowledged=acknowledged)
        marker = "SYNTHETIC-PROBE-fixed"
        own.build_context.return_value = SimpleNamespace(formatted_context=marker)
        other.build_context.return_value = SimpleNamespace(formatted_context=marker if leaked else "")
        error = RuntimeError("secret-token-and-uri")
        error.status = 500
        if failure == "initialize_client":
            sdk.Memory.side_effect = error
        elif failure == "record_turn":
            own.record_turn.side_effect = error
        elif failure == "same_session_context":
            own.build_context.side_effect = error
        elif failure == "other_session_context":
            other.build_context.side_effect = error
        elif failure == "close_client":
            sdk.Memory.return_value.__exit__.side_effect = error
        env = {"AGENT_ENGINE_URL": "https://agentengine.mongodb.com",
               "AGENT_ENGINE_PROJECT_ID": "synthetic", "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN": "secret"}
        with patch.dict(os.environ, env, clear=True), patch.dict("sys.modules", {"agent_engine_sdk_memory": sdk}), patch("uuid.uuid4", return_value=SimpleNamespace(hex="fixed")):
            report = run_live("engine", True)
        return report, own, other

    def test_failure_stages_preserve_write_uncertainty_and_stop(self):
        for stage, outcome in (("initialize_client", "not_attempted"), ("record_turn", "unknown"),
                               ("same_session_context", "acknowledged"),
                               ("other_session_context", "acknowledged"), ("close_client", "acknowledged")):
            with self.subTest(stage=stage):
                report, own, other = self.run_probe(stage)
                self.assertEqual(report["status"], "fail")
                self.assertEqual(report["failed_stage"], stage)
                self.assertEqual(report["write_outcome"], outcome)
                self.assertEqual(report["http_status"], 500)
                self.assertNotIn("secret", json.dumps(report))
                self.assertLessEqual(own.record_turn.call_count, 1)
                if stage in ("initialize_client", "record_turn", "same_session_context"):
                    other.build_context.assert_not_called()
                if stage == "record_turn":
                    own.build_context.assert_not_called()

    def test_success_requires_marker_and_separation(self):
        report, _, _ = self.run_probe()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["write_outcome"], "acknowledged")
        report, _, _ = self.run_probe(leaked=True)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["other_session_marker_absent"])

    def test_unacknowledged_write_is_not_claimed_as_accepted(self):
        report, own, other = self.run_probe(acknowledged=False)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["write_outcome"], "not_acknowledged")
        own.build_context.assert_not_called()
        other.build_context.assert_not_called()
        self.assertEqual(own.record_turn.call_count, 1)

    def test_context_budget_leaves_room_after_server_reserve(self):
        _, own, other = self.run_probe()
        for client in (own, other):
            self.assertGreaterEqual(client.build_context.call_args.kwargs["max_tokens"], 2048)
