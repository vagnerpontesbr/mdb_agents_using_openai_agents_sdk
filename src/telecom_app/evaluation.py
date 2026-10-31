"""Offline scoring of bounded observations; never an execution or approval authority."""

import hashlib
import math
from collections import Counter
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import Contract


class EvaluationCase(Contract):
    case_id: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=4000)
    specialists: tuple[Literal["financial", "technical", "sales"], ...] = Field(min_length=1)
    expected_text: str = Field(min_length=1, max_length=8000)


class EvaluationDataset(Contract):
    dataset_version: str
    reference_provenance: str
    reference_as_of: str
    cases: tuple[EvaluationCase, ...] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_cases(self) -> EvaluationDataset:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation case IDs")
        return self


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def measure(case: EvaluationCase, state: dict[str, Any] | None) -> dict[str, Any]:
    """Measure final contract/routing/text separately; do not infer unobserved tool facts."""
    text = state.get("text") if state else None
    names = state.get("specialists") if state else None
    valid = bool(
        state and state.get("status") == "completed"
        and state.get("outcome") in ("completed", "rejected", "expired", "needs_information")
        and isinstance(text, str) and len(text) <= 8000
        and isinstance(names, list)
        and all(name in ("financial", "technical", "sales") for name in names)
    )
    return {
        "final_contract_valid": valid,
        "routing_match": (
            set(names) == set(case.specialists) if valid and isinstance(names, list) else None),
        "outcome_completed": state.get("outcome") == "completed" if valid and state else None,
        "exact_reference_match": text == case.expected_text if valid else None,
        "response_sha256": fingerprint(text) if valid and isinstance(text, str) else None,
        "tool_parameter_accuracy": None,
        "independent_factual_correctness": None,
        "llm_judge_score": None,
    }


def rate(values: list[bool | None]) -> dict[str, int | float | None]:
    observed = [value for value in values if value is not None]
    passed = sum(observed)
    return {"attempts": len(values), "observed": len(observed), "passed": passed,
            "unavailable": len(values) - len(observed),
            "rate_on_observed": passed / len(observed) if observed else None,
            "passes_per_attempt": passed / len(values) if values else None}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {name: rate([row["metrics"][name] for row in rows]) for name in (
        "final_contract_valid", "routing_match", "outcome_completed", "exact_reference_match",
        "tool_parameter_accuracy", "independent_factual_correctness", "llm_judge_score",
    )}
    hashes = [row["metrics"]["response_sha256"] for row in rows
              if row["metrics"]["response_sha256"] is not None]
    pairs = len(hashes) * (len(hashes) - 1) // 2
    matching_pairs = sum(count * (count - 1) // 2 for count in Counter(hashes).values())
    durations = sorted(row["elapsed_seconds"] for row in rows)
    return {
        "metrics": metrics,
        "wording_repeatability": {"observed": len(hashes), "unique_texts": len(set(hashes)),
                                  "pairs": pairs, "matching_pairs": matching_pairs,
                                  "pair_agreement": matching_pairs / pairs if pairs else None},
        "latency_seconds": {
            "samples": len(durations),
            "p50_nearest_rank": (
                durations[math.ceil(len(durations) * .5) - 1] if durations else None),
            "maximum": max(durations) if durations else None,
        },
    }


def ranking_metrics(ranked: list[str], relevant: set[str], k: int) -> dict[str, float | None]:
    """Binary relevance; missing results penalize P@k; unknown gold is unavailable."""
    if k < 1 or len(set(ranked)) != len(ranked):
        raise ValueError("Positive k and unique ranked IDs required")
    top = ranked[:k]
    if not relevant:
        return dict(precision=None, recall=None, reciprocal_rank=None, ndcg=None)
    hits = [int(item in relevant) for item in top]
    dcg = sum(hit / math.log2(index + 2) for index, hit in enumerate(hits))
    ideal = sum(1 / math.log2(index + 2) for index in range(min(k, len(relevant))))
    return {"precision": sum(hits) / k, "recall": sum(hits) / len(relevant),
            "reciprocal_rank": next((1 / (i + 1) for i, hit in enumerate(hits) if hit), 0.0),
            "ndcg": dcg / ideal}
