"""Evidence semantics only; no provider compatibility is simulated as passing."""

import unittest

from scripts.check_memory_isolation import assess


class MemoryIsolationTests(unittest.TestCase):
    def observations(self):
        return {name: {"healthy": True, "marker_found": name in ("stm_positive", "durable_new_session")}
                for name in ("stm_positive", "stm_other_session", "stm_other_user",
                             "durable_new_session", "durable_other_user")}

    def test_success_requires_all_controls(self):
        self.assertTrue(all(c["status"] == "pass" for c in assess(self.observations())))

    def test_missing_durable_marker_blocks_negative_claim(self):
        observations = self.observations()
        observations["durable_new_session"]["marker_found"] = False
        checks = {c["check"]: c["status"] for c in assess(observations)}
        self.assertEqual(checks["durable_new_session"], "fail")
        self.assertEqual(checks["durable_other_user"], "blocked")
        self.assertEqual(checks["stm_other_session"], "pass")

    def test_leak_fails_even_without_positive_control(self):
        observations = self.observations()
        observations["stm_positive"]["marker_found"] = False
        observations["stm_other_user"]["marker_found"] = True
        checks = {c["check"]: c["status"] for c in assess(observations)}
        self.assertEqual(checks["stm_other_user"], "fail")

    def test_missing_or_degraded_response_cannot_pass(self):
        self.assertFalse(any(c["status"] == "pass" for c in assess({})))
        observations = self.observations()
        observations["stm_positive"]["healthy"] = False
        checks = {c["check"]: c["status"] for c in assess(observations)}
        self.assertEqual(checks["stm_positive"], "fail")
        self.assertEqual(checks["stm_other_session"], "blocked")
