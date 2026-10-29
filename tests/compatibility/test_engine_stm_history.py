"""STM retrieval summaries must not become SDK conversation history."""
import unittest
from scripts.check_engine_stm_history import assess


class StmHistoryTests(unittest.TestCase):
    def test_live_structural_loss_is_detected_without_content_logging(self):
        response = {"formatted_context": [{"role": "system", "content": "private"}],
                    "selected_memories": [
                        {"metadata": {"role": "user", "turn_seq": 1}},
                        {"metadata": {"role": "tool", "turn_seq": 3}},
                        {"metadata": {"role": "assistant", "turn_seq": 2,
                                      "tool_calls": {"tool_names": ["read"],
                                                     "tool_call_ids": ["id"],
                                                     "tool_calls_count": 1}}}]}
        result = assess(response)
        self.assertEqual(result["turn_sequences"], [1, 3, 2])
        self.assertIn("tool_result_correlation_missing", result["gaps"])
        self.assertIn("assistant_calls_are_summary_not_arguments", result["gaps"])
        self.assertIn("formatter_emits_privileged_role", result["gaps"])
        self.assertNotIn("private", str(result))

    def test_even_text_only_context_is_not_full_history_evidence(self):
        result = assess({"selected_memories": [{"metadata": {"role": "user"}}]})
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["sdk_restoration_proven"])

    def test_empty_context_is_explicit(self):
        self.assertIn("no_selected_turns", assess({})["gaps"])
