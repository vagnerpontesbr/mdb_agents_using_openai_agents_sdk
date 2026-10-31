"""Semantic cache evidence cannot hide rejected equivalents or false admissions."""

import json
from pathlib import Path

from scripts.run_phase5_semantic_validation import summary


def test_cache_metrics_separate_false_hits_and_missed_equivalents():
    rows = [{"equivalent": True, "hit": True}, {"equivalent": True, "hit": False},
            {"equivalent": False, "hit": True}, {"equivalent": False, "hit": False}]
    result = summary(rows)
    assert result["false_hits"] == 1
    assert result["missed_equivalents"] == 1
    assert result["precision"] == result["equivalent_recall"] == .5
    assert summary([])["precision"] is None


def test_semantic_dataset_partitions_do_not_share_queries():
    data = json.loads(Path("examples/telecom/evaluation/semantic-cache-v2.json").read_text())
    queries = {split: {case["query"] for group in data["groups"] if group["split"] == split
                      for case in group["cases"]} for split in ("development", "held_out")}
    assert queries["development"].isdisjoint(queries["held_out"])
    assert all(len(values) == 24 for values in queries.values())
    assert all(type(case["equivalent"]) is bool for group in data["groups"]
               for case in group["cases"])


def test_cached_candidate_loss_is_visible_before_reranking():
    from types import SimpleNamespace

    from scripts.run_phase5_source_recall import source_metrics

    candidates = [SimpleNamespace(version_key="wrong-source")]
    result = source_metrics(candidates, [0], ["required-source"])
    assert result["candidate_recall"] == 0
    assert result["top1"]["precision"] == 0
    assert result["top3"]["recall"] == 0


def test_source_recall_fixture_exceeds_cache_and_labels_existing_sources():
    data = json.loads(Path("examples/telecom/evaluation/cache-source-recall-v1.json").read_text())
    sources = {row["id"] for row in data["sources"]}
    assert len(sources) == 32 > 20
    for group in data["groups"]:
        for case in group["cases"]:
            assert set(case["relevant_sources"]) <= sources
            assert len(case["relevant_sources"]) == 1


def test_threshold_selection_rejects_validation_leakage_and_recall_loss():
    import pytest

    from scripts.phase5_calibration import select

    correct = {"candidate_recall": 1, "top1": {"precision": 1}}
    wrong = {"candidate_recall": 0, "top1": {"precision": 0}}
    rows = [{"partition": "development", "case_id": "paraphrase", "similarity": .986,
             "fresh": correct, "counterfactual_warm": correct},
            {"partition": "development", "case_id": "changed-product", "similarity": .98,
             "fresh": correct, "counterfactual_warm": wrong}]
    assert select(rows, [.99, .985, .98], .5)["selected"] == .985
    assert select(rows, [.99, .98], .5)["selected"] is None
    with pytest.raises(ValueError):
        select([{**rows[0], "partition": "held_out"}], [.98], .5)


def test_new_validation_queries_were_not_in_prior_experiments():
    path = Path("examples/telecom/evaluation/cache-source-calibration-v2.json")
    current = json.loads(path.read_text())
    new = {c["query"] for g in current["groups"] if g["id"] == "held_out" for c in g["cases"]}
    previous = set()
    for name in ("cache-source-recall-v1.json", "semantic-cache-v2.json"):
        data = json.loads(Path("examples/telecom/evaluation", name).read_text())
        previous.update(c["query"] for g in data["groups"] for c in g["cases"])
    assert new.isdisjoint(previous)


def test_selection_cannot_satisfy_reuse_only_in_one_group():
    from scripts.phase5_calibration import select

    correct = {"candidate_recall": 1, "top1": {"precision": 1}}
    rows = [{"partition": "development-a", "case_id": "paraphrase", "similarity": .99,
             "fresh": correct, "counterfactual_warm": correct},
            {"partition": "development-b", "case_id": "paraphrase", "similarity": .91,
             "fresh": correct, "counterfactual_warm": correct}]
    assert select(rows, [.98, .90], .5, per_group=True)["selected"] == .90


def test_v3_validation_is_new_after_promoting_old_validation_to_development():
    path = Path("examples/telecom/evaluation/cache-source-calibration-v3.json")
    data = json.loads(path.read_text())
    new = {c["query"] for g in data["groups"] if g["id"].startswith("held_out")
           for c in g["cases"]}
    seen = set()
    for name in ("cache-source-recall-v1.json", "cache-source-calibration-v2.json",
                 "semantic-cache-v2.json"):
        prior = json.loads(Path("examples/telecom/evaluation", name).read_text())
        seen.update(c["query"] for g in prior["groups"] for c in g["cases"])
    assert new.isdisjoint(seen)
    assert len(new) == 12  # Two negative-control questions are shared across groups.
    assert data["calibration_policy"]["minimum_per_group"] is True
