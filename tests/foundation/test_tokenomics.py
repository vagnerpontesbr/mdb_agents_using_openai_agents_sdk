"""Synthetic monetary contracts; no provider calls or fixture fallback."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from telecom_app.tokenomics import (
    Dashboard,
    DashboardView,
    Event,
    FocusPage,
    FocusRecord,
    Metric,
    Price,
    Section,
    Window,
    aggregate,
    anomaly_v1,
    ratio,
    standard_scenario,
)

NOW = datetime(2026, 11, 2, tzinfo=UTC)
WINDOW = Window(start=NOW - timedelta(days=7), end=NOW)


def metric(**updates):
    return Metric(**dict(dict(value=Decimal(10), unit="tokens", basis="observed",
                             source="synthetic", scope="telecom", observed_at=NOW,
                             window=WINDOW, coverage="complete"), **updates))


def price(**updates):
    return Price(**dict(dict(provider="openai", model="gpt-5.6-luna",
                            source_url="https://developers.openai.com/api/docs/pricing",
                            checked_at=NOW, context_band="short", input_per_million="0.20",
                            output_per_million="1.20"), **updates))


def test_exact_official_price_scenario():
    result = standard_scenario(model="gpt-5.6-luna", input_tokens=230660,
                               output_tokens=29214, price=price())
    assert result.amount_usd == Decimal("0.0811888")
    assert result.basis == "estimated"
    assert len(result.assumptions) == 4
    assert '"amount_usd":"0.0811888"' in result.model_dump_json()


def test_zero_usage_is_zero_estimate():
    assert standard_scenario(model="gpt-5.6-luna", input_tokens=0, output_tokens=0,
                             price=price()).amount_usd == 0


@pytest.mark.parametrize("usage", [-1, True, 0.5])
def test_invalid_usage_rejected(usage):
    with pytest.raises(ValueError):
        standard_scenario(model="gpt-5.6-luna", input_tokens=usage, output_tokens=1,
                          price=price())


def test_unknown_alias_and_unofficial_rate_rejected():
    with pytest.raises(ValueError):
        standard_scenario(model="gpt-5.6-luna-latest", input_tokens=1, output_tokens=1,
                          price=price())
    with pytest.raises(ValidationError):
        price(source_url="https://example.com/prices")
    with pytest.raises(ValidationError):
        price(provider="anthropic")


def test_anthropic_source_has_independent_rates():
    p = price(provider="anthropic", model="synthetic-claude",
              source_url="https://platform.claude.com/docs/en/about-claude/pricing",
              input_per_million="2", output_per_million="10")
    assert standard_scenario(model=p.model, input_tokens=1000000, output_tokens=1000000,
                             price=p).amount_usd == 12


@pytest.mark.parametrize("changes", [
    dict(value=None), dict(basis="unavailable"), dict(value="NaN"),
    dict(value="Infinity"), dict(value=-1), dict(value="0.5"),
    dict(unit="ratio", value=2), dict(currency="USD"),
    dict(unit="money"), dict(basis="billed"),
])
def test_invalid_metric_semantics(changes):
    with pytest.raises(ValidationError):
        metric(**changes)


def test_missing_is_not_zero_and_duplicates_are_not_added_twice():
    zero = Event(source_id="zero", metric=metric(value=0))
    missing = Event(source_id="missing", metric=metric(value=None, basis="unavailable",
                   coverage="unknown", reason="Not measured"))
    known = Event(source_id="known", metric=metric(value=7))
    assert aggregate((zero,)).value == 0
    assert aggregate((missing,)).value is None
    total = aggregate((known, known, zero, missing))
    assert total.value == 7
    assert total.coverage == "partial"
    assert total.reason
    with pytest.raises(ValueError):
        aggregate((known, Event(source_id="known", metric=metric(value=8))))


@pytest.mark.parametrize("change", [dict(unit="seconds"), dict(scope="other"),
                                      dict(source="other"), dict(basis="estimated")])
def test_mixed_streams_rejected(change):
    with pytest.raises(ValueError):
        aggregate((Event(source_id="a", metric=metric()),
                   Event(source_id="b", metric=metric(**change))))


def test_mixed_currencies_and_ratios_rejected():
    with pytest.raises(ValueError):
        aggregate(tuple(Event(source_id=c, metric=metric(unit="money", currency=c))
                        for c in ("USD", "EUR")))
    with pytest.raises(ValueError):
        aggregate((Event(source_id="a", metric=metric(unit="ratio", value="0.5")),))


def test_window_bounds_timezone_and_denominators():
    for start in (NOW, NOW - timedelta(days=91), NOW + timedelta(days=1)):
        with pytest.raises(ValidationError):
            Window(start=start, end=NOW)
    with pytest.raises(ValidationError):
        Window(start=NOW.replace(tzinfo=None), end=NOW)
    assert ratio(0, 0) is None
    assert ratio(0, 1) == 0
    assert ratio(1, 4) == Decimal("0.25")
    with pytest.raises(ValueError):
        ratio(2, 1)


def test_anomalies_need_comparable_baseline_and_strict_threshold():
    assert anomaly_v1(Decimal(100), (Decimal(1),) * 6) is None
    assert anomaly_v1(Decimal(100), (Decimal(0),) * 7) is None
    assert anomaly_v1(Decimal(2), (Decimal(1),) * 7) is False
    assert anomaly_v1(Decimal("2.01"), (Decimal(1),) * 7) is True
    with pytest.raises(ValueError):
        anomaly_v1(Decimal("NaN"), ())


def kpis():
    return Dashboard(total_cost=metric(unit="money", currency="USD"),
                     observed_tokens=metric(),
                     average_cost_per_execution=metric(unit="money", currency="USD"),
                     cache_hit_ratio=metric(unit="ratio", value="0.5"),
                     token_goodput=metric(unit="ratio", value="0.5"),
                     execution_count=metric(unit="executions"), partial=True)


def test_all_sections_explicit_and_partial():
    section = Section(status="unavailable", reason="Not measured")
    sections = dict.fromkeys(("applications", "daily", "anomalies", "context",
                             "token_categories", "models", "agents", "intents"), section)
    view = DashboardView(kpis=kpis(), **sections)
    assert view.context.rows == ()
    with pytest.raises(ValidationError):
        DashboardView(kpis=Dashboard(**dict(kpis().model_dump(), partial=False)), **sections)
    with pytest.raises(ValidationError):
        Section(status="unavailable")
    with pytest.raises(ValidationError):
        Section(status="available")


def test_estimated_total_requires_matching_provenance():
    section = Section(status="empty")
    sections = dict.fromkeys(("applications", "daily", "anomalies", "context",
                             "token_categories", "models", "agents", "intents"), section)
    estimate = standard_scenario(model="gpt-5.6-luna", input_tokens=1, output_tokens=1,
                                 price=price())
    totals = Dashboard(**dict(kpis().model_dump(), total_cost=metric(
        unit="money", currency="USD", basis="estimated", value=estimate.amount_usd)))
    with pytest.raises(ValidationError):
        DashboardView(kpis=totals, **sections)
    assert DashboardView(kpis=totals, estimate=estimate, **sections).estimate == estimate


def test_focus_never_relables_estimate_as_billed_and_preserves_units():
    estimated = metric(unit="money", currency="USD", basis="estimated")
    absent = metric(unit="money", currency="USD", value=None, basis="unavailable",
                    reason="No invoice", coverage="unknown")
    record = FocusRecord(record_id="one", provider="synthetic", sku="audio",
                         consumed=metric(unit="seconds"), billed_cost=absent,
                         estimated_cost=estimated)
    assert record.billed_cost.value is None
    assert record.consumed.unit == "seconds"
    with pytest.raises(ValidationError):
        FocusRecord(**dict(record.model_dump(), billed_cost=estimated))
    with pytest.raises(ValidationError):
        FocusPage(records=(record, record), status="available")
    with pytest.raises(ValidationError):
        FocusPage(records=(record,) * 101, status="available")
    assert FocusPage(status="unavailable", reason="No native records").records == ()
