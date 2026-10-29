"""Reject mismatched Engine actions/results before synthetic approval/speech."""
import copy
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch

from scripts import check_voice_engine as probe


def envelope():
    return {"success": True, "project_id": probe.PROJECT, "org_id": probe.ORG,
            "workspace_id": probe.WORKSPACE, "session_id": "synthetic-session",
            "execution_id": "synthetic-execution"}


def pending():
    return {**envelope(), "suspended": True, "suspend_context": {"interrupts": [{
        "id": "synthetic-review", "value": {
            "contract": "openai-engine-review-v1", "requesting_user_id": probe.USER,
            "allowed_decisions": ["approve", "reject"], "action": {
                "arguments": copy.deepcopy(probe.EXPECTED), "tool_call_id": "release-demo-1",
                "tool_name": "release_synthetic_recall"}}}]}}


class VoiceEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_action_never_sends_resume(self):
        for field, value in (("amount_minor", 1), ("model_reported_marker", "invented"),
                             ("invoice_id", "customer-invoice")):
            response = pending()
            response["suspend_context"]["interrupts"][0]["value"]["action"]["arguments"][field] = value
            call = AsyncMock(return_value=response)
            with patch.object(probe, "invoke_cli", call), self.assertRaises(ValueError):
                await probe.engine_turn("synthetic-session", "synthetic request", [])
            self.assertEqual(call.await_count, 1)

    async def test_exact_review_and_result_complete_before_speech(self):
        complete = {**envelope(), "response": json.dumps(probe.EXPECTED)}
        calls = []
        remote = AsyncMock(side_effect=[pending(), complete])
        with patch.object(probe, "invoke_cli", remote):
            answer = await probe.engine_turn("synthetic-session", "synthetic request", calls)
        self.assertEqual(answer, probe.SPOKEN)
        self.assertTrue(calls[0]["completed"])
        self.assertEqual(remote.await_args_list[1].kwargs, {"review": "synthetic-review"})

    async def test_changed_execution_or_scope_releases_no_speech(self):
        for field in ("execution_id", "session_id", "workspace_id", "org_id", "project_id"):
            complete = {**envelope(), "response": json.dumps(probe.EXPECTED), field: "other"}
            with self.subTest(field=field), self.assertRaises(ValueError):
                probe.validate_completed(complete, "synthetic-session", "synthetic-execution")

    async def test_wrong_requester_or_extra_review_blocks(self):
        response = pending()
        response["suspend_context"]["interrupts"][0]["value"]["requesting_user_id"] = "other"
        with self.assertRaises(ValueError):
            probe.validate_pending(response, "synthetic-session")
        response = pending()
        response["suspend_context"]["interrupts"] *= 2
        with self.assertRaises(ValueError):
            probe.validate_pending(response, "synthetic-session")

    async def test_live_is_explicit(self):
        run = subprocess.run([sys.executable, "scripts/check_voice_engine.py"],
                             capture_output=True, text=True, env={"PATH": os.defpath})
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
