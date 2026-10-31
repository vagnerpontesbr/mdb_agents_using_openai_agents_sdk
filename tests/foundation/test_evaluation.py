"""Metric counterexamples: repetition, stale gold and missing evidence are distinct."""

import pytest

from telecom_app.evaluation import EvaluationCase, measure, ranking_metrics, rate, summarize

CASE = EvaluationCase(case_id="invoice", question="Invoice?", specialists=("financial",),
                      expected_text="USD 79.90")


def result(text="USD 79.90", specialists=None):
    return {"status": "completed", "outcome": "completed", "text": text,
            "specialists": specialists if specialists is not None else ["financial"]}


def test_identical_wrong_answers_are_repeatable_but_fail_reference():
    rows = [{"metrics": measure(CASE, result("USD 1.00")), "elapsed_seconds": 1.0}
            for _ in range(3)]
    summary = summarize(rows)
    assert summary["wording_repeatability"]["pair_agreement"] == 1
    assert summary["metrics"]["exact_reference_match"]["passed"] == 0
    assert summary["metrics"]["independent_factual_correctness"]["observed"] == 0


def test_failures_are_not_dropped_from_denominators():
    assert rate([True, None, False]) == {
        "attempts": 3, "observed": 2, "passed": 1, "unavailable": 1,
        "rate_on_observed": .5, "passes_per_attempt": 1 / 3}
    assert measure(CASE, None)["final_contract_valid"] is False
    assert measure(CASE, None)["exact_reference_match"] is None


def test_routing_and_schema_do_not_imply_correct_answer():
    metrics = measure(CASE, result("Wrong", ["sales"]))
    assert metrics["final_contract_valid"] is True
    assert metrics["routing_match"] is False
    assert metrics["exact_reference_match"] is False
    assert metrics["tool_parameter_accuracy"] is None


def test_empty_and_single_observation_do_not_claim_repeatability():
    assert summarize([])["wording_repeatability"]["pair_agreement"] is None
    rows = [{"metrics": measure(CASE, result()), "elapsed_seconds": 2.0}]
    assert summarize(rows)["wording_repeatability"]["pair_agreement"] is None


def test_stale_gold_can_look_perfect_while_current_gold_fails():
    stale = ranking_metrics(["obsolete-v1"], {"obsolete-v1"}, 1)
    current = ranking_metrics(["obsolete-v1"], {"current-v2"}, 1)
    assert all(value == 1 for value in stale.values())
    assert all(value == 0 for value in current.values())


def test_ranking_bounds_and_unknown_gold():
    scores = ranking_metrics(["irrelevant", "relevant"], {"relevant", "missing"}, 3)
    assert scores["precision"] == 1 / 3
    assert scores["recall"] == .5
    assert scores["reciprocal_rank"] == .5
    assert all(value is None for value in ranking_metrics([], set(), 1).values())
    with pytest.raises(ValueError):
        ranking_metrics(["duplicate", "duplicate"], {"duplicate"}, 2)


def test_runner_dry_run_never_opens_database_or_creates_report(tmp_path, monkeypatch, capsys):
    import scripts.run_phase5_evaluation as runner

    def denied(*args, **kwargs):
        raise AssertionError("Dry run accessed MongoDB")

    destination = tmp_path / "report.json"
    monkeypatch.setattr(runner, "MongoClient", denied)
    monkeypatch.setattr("sys.argv", ["evaluation", "--output", str(destination)])
    runner.main()
    assert not destination.exists()
    assert '"live_calls": 0' in capsys.readouterr().out


def test_live_runner_refuses_overwriting_evidence_before_any_calls(tmp_path, monkeypatch):
    import scripts.run_phase5_evaluation as runner

    def denied(*args, **kwargs):
        raise AssertionError("Provider admission preceded evidence reservation")

    destination = tmp_path / "report.json"
    destination.write_text("prior evidence")
    monkeypatch.setattr(runner, "MongoClient", denied)
    monkeypatch.setattr("sys.argv", ["evaluation", "--allow-live", "--output", str(destination)])
    with pytest.raises(FileExistsError):
        runner.main()
    assert destination.read_text() == "prior evidence"


@pytest.mark.parametrize("status,session", [("running", "ours"), ("suspended", "ours"),
                                           ("completed", "someone-else")])
def test_runtime_cleanup_refuses_active_or_foreign_sessions(status, session):
    from scripts.run_phase5_evaluation import release_completed_runtime

    class Engine:
        def execution(self, execution):
            return {"status": status, "session_id": session}

        def call(self, *args):
            pytest.fail("Must not stop an active or foreign session")

    with pytest.raises(ValueError):
        release_completed_runtime(Engine(), "ours", "execution")


def test_runtime_cleanup_waits_for_native_release(monkeypatch):
    from scripts import run_phase5_evaluation as runner

    calls = []
    snapshots = iter([[{"session_id": "ours"}], [{"session_id": "ours"}], []])

    class Engine:
        def execution(self, execution):
            return {"status": "completed", "session_id": "ours"}

        def call(self, path, *args):
            calls.append(path)
            return {"status": "stopping"} if path.endswith("/stop") else {
                "sessions": next(snapshots)}

    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    assert runner.release_completed_runtime(Engine(), "ours", "execution") == "released"
    assert sum(path.endswith("/ours/stop") for path in calls) == 1
