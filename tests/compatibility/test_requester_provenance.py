"""Fail-closed checks for sanitized invocation provenance diagnostics."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "requester_provenance", Path(__file__).parents[2] / "scripts/check_requester_provenance.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RequesterProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"user_id": "authenticated-fixture"}
        self.run = {"execution_id": "execution", "session_id": "session", "workspace_id": "workspace",
                    "user_id": "delegated-fixture", "invoker_user_id": "authenticated-fixture"}
        self.response = {"count": 1, "truncated": False, "runs": [self.run]}

    def assess(self):
        return MODULE.assess(self.profile, self.response, execution="execution", session="session",
                             workspace="workspace", delegated_user="delegated-fixture")

    def test_observation_does_not_authorize_and_excludes_identifiers(self):
        result = self.assess()
        self.assertEqual(result["status"], "observed")
        self.assertFalse(result["requester_approval_authorized"])
        self.assertNotIn("authenticated-fixture", str(result))
        self.assertNotIn("delegated-fixture", str(result))

    def test_missing_or_spoofed_invoker_is_blocked(self):
        for value in (None, "", "delegated-fixture", "other-reader"):
            with self.subTest(value=value):
                self.run["invoker_user_id"] = value
                self.assertEqual(self.assess()["status"], "blocked")

    def test_wrong_scope_or_delegation_is_blocked(self):
        for field in ("execution_id", "session_id", "workspace_id", "user_id"):
            with self.subTest(field=field):
                original = self.run[field]
                self.run[field] = "other"
                self.assertEqual(self.assess()["status"], "blocked")
                self.run[field] = original

    def test_truncated_missing_count_or_duplicate_is_blocked(self):
        for response in ({"runs": [self.run]}, {"count": 1, "truncated": True, "runs": [self.run]},
                         {"count": 2, "truncated": False, "runs": [self.run, self.run]}):
            self.response = response
            self.assertEqual(self.assess()["status"], "blocked")
