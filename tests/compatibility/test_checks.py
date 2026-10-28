"""Tests for evidence semantics and prevention of accidental live calls."""

import json
import os
import unittest
from unittest.mock import patch

from scripts.check_compatibility import allows_python, build_report, exit_code, run_live


class CompatibilityChecks(unittest.TestCase):
    def test_detects_voyage_python_upper_bound(self):
        self.assertFalse(allows_python("<3.15,>=3.9", "3.15.2"))
        self.assertTrue(allows_python("<3.15,>=3.9", "3.14.6"))

    def test_unknown_constraint_is_not_assumed_supported(self):
        with self.assertRaises(ValueError):
            allows_python("~=3.14", "3.15.2")

    def test_live_calls_need_explicit_flag(self):
        with patch("scripts.check_compatibility.probe_openai") as call:
            self.assertEqual(run_live("openai", False)["status"], "blocked")
            call.assert_not_called()

    def test_exception_secrets_are_not_reported(self):
        with patch("scripts.check_compatibility.probe_mongodb", side_effect=RuntimeError("secret-password")):
            report = run_live("mongodb", True)
        self.assertEqual(report["status"], "fail")
        self.assertNotIn("secret-password", json.dumps(report))

    def test_missing_credentials_block_without_importing_sdk(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(run_live("openai", True)["status"], "blocked")
            self.assertEqual(run_live("mongodb", True)["status"], "blocked")
            self.assertEqual(run_live("engine", True)["status"], "blocked")
            self.assertEqual(run_live("engine-context", True)["status"], "blocked")
            self.assertEqual(run_live("voyage", True)["status"], "blocked")

    def test_report_contains_presence_not_credentials(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret-test-value"}, clear=True):
            report = build_report("openai", False)
        self.assertTrue(report["configuration_presence"]["OPENAI_API_KEY"])
        self.assertNotIn("secret-test-value", json.dumps(report))
        self.assertFalse(report["phase0_complete"])

    def test_failed_or_blocked_is_not_a_success(self):
        self.assertEqual(exit_code({"checks": [{"status": "pass"}, {"status": "blocked"}]}), 2)
        self.assertEqual(exit_code({"checks": [{"status": "fail"}, {"status": "blocked"}]}), 1)
        self.assertEqual(exit_code({"checks": [{"status": "pass"}]}), 0)

    def test_context_probe_is_opt_in(self):
        with patch("scripts.check_compatibility.probe_engine_context") as call:
            self.assertEqual(run_live("engine-context", False)["status"], "blocked")
            call.assert_not_called()

    def test_auth_error_code_is_allowlisted(self):
        for code in ("INVALID_TOKEN", "secret-test-value"):
            error = RuntimeError("secret-test-value")
            error.status = 401
            error.code = code
            with patch("scripts.check_compatibility.probe_engine_context", side_effect=error):
                report = run_live("engine-context", True)
            self.assertEqual(report["http_status"], 401)
            self.assertEqual(report["error_code"], "INVALID_TOKEN" if code == "INVALID_TOKEN" else None)
            self.assertNotIn("secret-test-value", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
