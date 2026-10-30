"""Native generation-pinned resume envelope versus legacy per-interrupt answers."""
import json
import unittest

from pydantic import ValidationError

from openai_engine_adapter.review import recorded_review_decision
from openai_engine_adapter.adapter import UnsupportedContract


class NativeReviewAnswerTests(unittest.TestCase):
    def test_native_approved_and_rejected_are_exact_domain_decisions(self):
        for recorded, expected in [('approved', 'approve'), ('rejected', 'reject')]:
            answer = json.dumps({'human_review': {'decision': recorded, 'reviewer_notes': ''}})
            self.assertEqual(recorded_review_decision(answer).decision, expected)

    def test_legacy_per_interrupt_contract_is_preserved(self):
        for decision in ('approve', 'reject'):
            self.assertEqual(recorded_review_decision({'decision': decision}).decision, decision)

    def test_unknown_or_injected_envelopes_never_become_approval(self):
        for value in [
            'approve', '{"decision":"approve"}', '{}',
            json.dumps({'human_review': {'decision': 'approve', 'reviewer_notes': ''}}),
            json.dumps({'human_review': {'decision': True, 'reviewer_notes': ''}}),
            json.dumps({'human_review': {'decision': 'approved', 'reviewer_notes': '', 'user_id': 'other'}}),
            json.dumps({'human_review': {'decision': 'approved', 'reviewer_notes': ''}, 'action': {}}),
            'x' * 10001,
        ]:
            with self.subTest(value=value[:80]), self.assertRaises((ValidationError, UnsupportedContract)):
                recorded_review_decision(value)
