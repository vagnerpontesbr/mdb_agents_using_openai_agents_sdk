"""Grader failures and source fidelity must not become current factual approval."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from telecom_app.evaluation_judge import Judgment, grade


@pytest.mark.parametrize("status,parsed", [("incomplete", None), ("completed", None)])
def test_incomplete_or_refused_judge_is_unavailable(status, parsed):
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(status=status, output_parsed=parsed)
    with pytest.raises(ValueError, match="Judge refused"):
        grade(client, question="Question", answer="Answer", source="Source",
              current_reference="Current reference")


def test_faithfulness_does_not_imply_current_correctness_or_enable_tools():
    client = Mock()
    decision = Judgment(faithful_to_source=True, correct_for_current_reference=False,
                        rationale="The source is obsolete.")
    client.responses.parse.return_value = SimpleNamespace(
        status="completed", output_parsed=decision, usage=None, id="synthetic", model="synthetic")
    result, usage = grade(client, question="Question", answer="Legacy reset", source="Legacy reset",
                          current_reference="Never reset")
    assert result.faithful_to_source and not result.correct_for_current_reference
    args = client.responses.parse.call_args.kwargs
    assert args["store"] is False and "tools" not in args
    assert args["max_output_tokens"] == 1200
    assert usage["total_tokens"] is None


def test_judge_strings_cannot_masquerade_as_boolean_grades():
    with pytest.raises(ValidationError):
        Judgment.model_validate({"faithful_to_source": "true",
                                 "correct_for_current_reference": True,
                                 "rationale": "Synthetic."})
