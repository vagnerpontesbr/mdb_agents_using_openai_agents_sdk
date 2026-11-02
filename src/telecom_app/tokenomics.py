"""TOK-0 normalized contracts and arithmetic; no live adapter or trace storage."""

from datetime import timedelta
from decimal import Decimal
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .contracts import Contract

Basis = Literal["observed", "estimated", "billed", "unavailable"]
Unit = Literal["tokens", "seconds", "calls", "executions", "ratio", "money"]


class Window(Contract):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if not timedelta(0) < self.end - self.start <= timedelta(days=90):
            raise ValueError("Window must be positive and at most 90 days")
        return self


class Metric(Contract):
    value: Decimal | None = Field(default=None, allow_inf_nan=False)
    unit: Unit
    basis: Basis
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=200)
    observed_at: AwareDatetime
    window: Window
    coverage: Literal["complete", "partial", "unknown"]
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.value is None) != (self.basis == "unavailable"):
            raise ValueError("Unavailable metrics must have null values")
        if self.value is None and not self.reason:
            raise ValueError("Missing values require an explanation")
        if (self.unit == "money") != (self.currency is not None):
            raise ValueError("Only money requires a currency")
        if self.value is not None:
            if self.unit != "money" and self.value < 0:
                raise ValueError("Negative usage is invalid")
            if self.unit == "ratio" and self.value > 1:
                raise ValueError("Ratios must be between zero and one")
            if self.unit in ("tokens", "calls", "executions"):
                if self.value != self.value.to_integral_value():
                    raise ValueError("Counts must be integral")
        if self.basis == "billed" and self.unit != "money":
            raise ValueError("Billed basis applies only to monetary values")
        return self


class Event(Contract):
    """A normalized leaf event; adapters must prove scope and stable source identity."""

    source_id: str = Field(min_length=1, max_length=200)
    metric: Metric


class Dashboard(Contract):
    schema_version: Literal[1] = 1
    total_cost: Metric
    observed_tokens: Metric
    average_cost_per_execution: Metric
    cache_hit_ratio: Metric
    token_goodput: Metric
    execution_count: Metric
    partial: bool

    @model_validator(mode="after")
    def kpi_units(self) -> Self:
        expected: tuple[tuple[Metric, Unit], ...] = (
            (self.total_cost, "money"), (self.observed_tokens, "tokens"),
            (self.average_cost_per_execution, "money"), (self.cache_hit_ratio, "ratio"),
            (self.token_goodput, "ratio"), (self.execution_count, "executions"),
        )
        for metric, unit in expected:
            if metric.unit != unit:
                raise ValueError("Incorrect KPI unit")
            if metric.scope != self.total_cost.scope or metric.window != self.total_cost.window:
                raise ValueError("KPIs must share scope and window")
        incomplete = any(m.coverage != "complete" or m.value is None for m, _ in expected)
        if incomplete and not self.partial:
            raise ValueError("Incomplete coverage must be explicit")
        return self


def aggregate(events: tuple[Event, ...]) -> Metric:
    """Sum one disjoint stream; never combine totals with their child events."""
    if not events or len(events) > 1000:
        raise ValueError("Expected between 1 and 1000 events")
    first = events[0].metric
    if first.unit == "ratio":
        raise ValueError("Ratios require original operands, not addition")
    unique: dict[str, Event] = {}
    for event in events:
        metric = event.metric
        for field in ("unit", "currency", "source", "scope", "window"):
            if getattr(metric, field) != getattr(first, field):
                raise ValueError("Mixed units, sources, scope or windows cannot be summed")
        if event.source_id in unique and unique[event.source_id] != event:
            raise ValueError("Conflicting duplicate source identity")
        unique[event.source_id] = event
    metrics = [e.metric for e in unique.values()]
    known = [m for m in metrics if m.value is not None]
    if len({m.basis for m in known}) > 1:
        raise ValueError("Observed, estimated and billed values cannot be mixed")
    complete = len(known) == len(metrics) and all(m.coverage == "complete" for m in metrics)
    return Metric(
        value=sum((m.value for m in known if m.value is not None), Decimal(0)) if known else None,
        unit=first.unit, currency=first.currency, source=first.source, scope=first.scope,
        observed_at=max(m.observed_at for m in metrics), window=first.window,
        basis=known[0].basis if known else "unavailable",
        coverage="complete" if complete else "partial" if known else "unknown",
        reason=None if complete else "Incomplete source coverage; known values are a subtotal",
    )


def ratio(numerator: int, denominator: int) -> Decimal | None:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("Invalid ratio operands")
    return Decimal(numerator) / Decimal(denominator) if denominator else None


def anomaly_v1(current: Decimal, baseline: tuple[Decimal, ...]) -> bool | None:
    """Seven complete comparable UTC days; current > 2x their positive mean."""
    if not current.is_finite() or current < 0:
        raise ValueError("Invalid current observation")
    if any(not value.is_finite() or value < 0 for value in baseline):
        raise ValueError("Invalid baseline observation")
    if len(baseline) != 7:
        return None
    mean = sum(baseline, Decimal(0)) / 7
    return current > 2 * mean if mean else None


class Price(Contract):
    """Reviewed public rate; never a provider invoice or fuzzy model alias."""

    provider: Literal["openai", "anthropic"]
    model: str = Field(min_length=1, max_length=100)
    source_url: str
    checked_at: AwareDatetime
    currency: Literal["USD"] = "USD"
    input_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    output_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    context_band: Literal["short", "long"]
    service_tier: Literal["standard"] = "standard"

    @model_validator(mode="after")
    def official_source(self) -> Self:
        sources = {
            "openai": "https://developers.openai.com/api/docs/pricing",
            "anthropic": "https://platform.claude.com/docs/en/about-claude/pricing",
        }
        if self.source_url != sources[self.provider]:
            raise ValueError("Price must reference the approved provider source")
        return self


class Estimate(Contract):
    amount_usd: Decimal = Field(ge=0, allow_inf_nan=False)
    basis: Literal["estimated"] = "estimated"
    price: Price
    assumptions: tuple[str, ...] = Field(min_length=1, max_length=10)


def standard_scenario(
    *, model: str, input_tokens: int, output_tokens: int, price: Price,
) -> Estimate:
    """Explicit regular-input scenario; no inferred cache, geography or invoice cost."""
    if model != price.model:
        raise ValueError("Exact model rate required")
    if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
        raise ValueError("Nonnegative integral usage required")
    return Estimate(
        amount_usd=(input_tokens * price.input_per_million
                    + output_tokens * price.output_per_million) / Decimal(1_000_000),
        price=price,
        assumptions=(
            "All input treated as regular uncached input; cache reads/writes unknown",
            f"Standard service, {price.context_band} context assumed per request",
            "No regional uplift, gateway markup, discounts, taxes or non-token charges",
            "Current price snapshot; historical tariff effectiveness not verified",
        ),
    )


class BreakdownRow(Contract):
    key: str = Field(min_length=1, max_length=100)
    metric: Metric


class Section(Contract):
    """Empty and unsupported sections remain explicit in the response."""

    status: Literal["available", "empty", "unavailable", "partial"]
    rows: tuple[BreakdownRow, ...] = Field(default=(), max_length=100)
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def rows_match_status(self) -> Self:
        if self.status in ("empty", "unavailable") and self.rows:
            raise ValueError("Empty/unavailable sections cannot contain rows")
        if self.status == "available" and not self.rows:
            raise ValueError("Use empty for a measured empty section")
        if self.status in ("unavailable", "partial") and not self.reason:
            raise ValueError("Incomplete sections require a reason")
        if len({row.key for row in self.rows}) != len(self.rows):
            raise ValueError("Duplicate section keys")
        return self


class DashboardView(Contract):
    schema_version: Literal[1] = 1
    kpis: Dashboard
    applications: Section
    daily: Section
    anomalies: Section
    context: Section
    token_categories: Section
    models: Section
    agents: Section
    intents: Section
    estimate: Estimate | None = None

    @model_validator(mode="after")
    def consistent_sections(self) -> Self:
        sections = (self.applications, self.daily, self.anomalies, self.context,
                    self.token_categories, self.models, self.agents, self.intents)
        if any(s.status in ("partial", "unavailable") for s in sections) and not self.kpis.partial:
            raise ValueError("Dashboard must disclose incomplete sections")
        for section in sections:
            for row in section.rows:
                if (row.metric.scope != self.kpis.total_cost.scope
                        or row.metric.window != self.kpis.total_cost.window):
                    raise ValueError("Section scope/window mismatch")
        if self.kpis.total_cost.basis == "estimated":
            if self.estimate is None or self.estimate.amount_usd != self.kpis.total_cost.value:
                raise ValueError("Estimated total needs matching price and assumptions")
        elif self.estimate is not None:
            raise ValueError("Estimate cannot label a non-estimated total")
        return self


class FocusRecord(Contract):
    record_id: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=100)
    consumed: Metric
    billed_cost: Metric
    estimated_cost: Metric | None = None

    @model_validator(mode="after")
    def separated_costs(self) -> Self:
        if self.consumed.unit not in ("tokens", "seconds", "calls"):
            raise ValueError("Unsupported consumption unit")
        for cost in (self.billed_cost, self.estimated_cost):
            if cost is not None and (
                cost.unit != "money" or cost.window != self.consumed.window
                or cost.scope != self.consumed.scope
            ):
                raise ValueError("Cost must match consumption scope/window")
        if self.billed_cost.basis not in ("billed", "unavailable"):
            raise ValueError("Billed cost cannot contain an estimate")
        if self.estimated_cost is not None and self.estimated_cost.basis != "estimated":
            raise ValueError("Estimated cost needs estimated basis")
        return self


class FocusPage(Contract):
    schema_version: Literal[1] = 1
    records: tuple[FocusRecord, ...] = Field(default=(), max_length=100)
    next_cursor: str | None = Field(default=None, max_length=500)
    status: Literal["available", "empty", "unavailable", "partial"]
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def pagination(self) -> Self:
        if self.status in ("empty", "unavailable") and (self.records or self.next_cursor):
            raise ValueError("Empty/unavailable pages cannot contain records or cursors")
        if self.status == "available" and not self.records:
            raise ValueError("Use empty for no records")
        if self.status in ("partial", "unavailable") and not self.reason:
            raise ValueError("Incomplete pages require a reason")
        if len({r.record_id for r in self.records}) != len(self.records):
            raise ValueError("Duplicate focus identities")
        return self
