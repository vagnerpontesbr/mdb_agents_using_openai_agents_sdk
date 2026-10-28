"""Authentication evidence classification; these tests make no provider calls."""

import os
import unittest
from unittest.mock import patch

from scripts.check_compatibility import assess_engine_auth, run_live


class EngineAuthTests(unittest.TestCase):
    def statuses(self):
        return {"valid": 200, "missing": 401, "invalid": 401, "different_project": 403}

    def test_expired_positive_control_cannot_pass(self):
        statuses = self.statuses()
        statuses["valid"] = 401
        self.assertEqual(assess_engine_auth(statuses)["status"], "fail")

    def test_not_found_or_server_failure_is_not_an_authorization_denial(self):
        for status in (200, 401, 404, 500):
            statuses = self.statuses()
            statuses["different_project"] = status
            self.assertEqual(assess_engine_auth(statuses)["status"], "fail")

    def test_all_observations_are_required(self):
        self.assertEqual(assess_engine_auth(self.statuses())["status"], "pass")
        self.assertEqual(assess_engine_auth({})["status"], "fail")
        for name in ("missing", "invalid"):
            statuses = self.statuses()
            statuses[name] = 200
            self.assertEqual(assess_engine_auth(statuses)["status"], "fail")

    def test_live_gate_and_missing_configuration(self):
        with patch("scripts.check_compatibility.probe_engine_auth") as probe:
            self.assertEqual(run_live("engine-auth", False)["status"], "blocked")
            probe.assert_not_called()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(run_live("engine-auth", True)["status"], "blocked")
