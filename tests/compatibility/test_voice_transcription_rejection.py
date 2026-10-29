"""Speech rejection remains private, pre-dispatch and bounded for retries."""
import json
import unittest
from scripts.check_voice_engine import MARKER, PROMPT, UnexpectedTranscript, validate_transcription
from scripts.serve_voice_engine_probe import reject_transcription


class TranscriptRejectionTests(unittest.TestCase):
    def test_fixture_and_case_variation_accepted(self):
        validate_transcription(PROMPT)
        validate_transcription(PROMPT.upper())

    def test_missing_words_report_contains_no_transcript(self):
        raw = 'private-input-that-must-not-be-logged'
        with self.assertRaises(UnexpectedTranscript) as result:
            validate_transcription(raw)
        state = {'calls': [], 'voice_attempts': 1}
        response = reject_transcription(state, result.exception)
        self.assertEqual(response['missing_words'], ['invoice', 'synthetic', 'marker'])
        self.assertTrue(response['retryable'])
        self.assertEqual(state['status'], 'not_started')
        self.assertNotIn(raw, json.dumps(state) + json.dumps(response) + str(result.exception))

    def test_empty_oversize_and_marker_echo_rejected(self):
        for value, reason in [('', 'no_speech'), ('  ', 'no_speech'),
                              ('a' * 301, 'outside_fixture'), (MARKER, 'outside_fixture')]:
            with self.subTest(reason=reason), self.assertRaises(UnexpectedTranscript) as result:
                validate_transcription(value)
            self.assertEqual(result.exception.reason, reason)

    def test_no_retry_after_remote_work_or_third_input(self):
        for calls, attempts in [([{'completed': False}], 1), ([], 3)]:
            state = {'calls': calls, 'voice_attempts': attempts}
            response = reject_transcription(state, UnexpectedTranscript('no_speech'))
            self.assertFalse(response['retryable'])
            self.assertEqual(state['status'], 'failed_or_incomplete')
