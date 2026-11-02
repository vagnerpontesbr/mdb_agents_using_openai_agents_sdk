"""Bounded read-only Engine usage projection; no trace storage or provider invocation."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal, Protocol
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from compatibility.demo_auth.engine import BASE, PROJECT, WORKSPACE, NoRedirect

from .tokenomics import (
    BreakdownRow,
    Dashboard,
    DashboardView,
    FocusPage,
    Metric,
    Price,
    Section,
    Unit,
    Window,
    standard_scenario,
)

Period = Literal["7d", "30d", "90d"]
SCOPE = "telecom_workspace"
SOURCE = "agent_engine_cost_dashboard"


class TokenomicsUnavailable(Exception):
    def __init__(self, code: str = "tokenomics_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class TokenomicsRangeUnsupported(ValueError):
    pass


class NativeModel(BaseModel):
    # Unknown upstream fields are never returned or persisted.
    model_config = ConfigDict(extra="ignore")


class Summary(NativeModel):
    total_tokens: int = Field(ge=0, strict=True)
    total_prompt_tokens: int = Field(ge=0, strict=True)
    total_completion_tokens: int = Field(ge=0, strict=True)
    total_llm_calls: int = Field(ge=0, strict=True)
    unpriced_llm_calls: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def consistent(self) -> Summary:
        if self.total_tokens != self.total_prompt_tokens + self.total_completion_tokens:
            raise ValueError("Inconsistent token categories")
        if self.unpriced_llm_calls > self.total_llm_calls:
            raise ValueError("Inconsistent call coverage")
        return self


class ModelUsage(NativeModel):
    model: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,99}$")
    total_tokens: int = Field(ge=0, strict=True)
    call_count: int = Field(ge=0, strict=True)


class WorkspaceUsage(NativeModel):
    workspace_id: str
    total_tokens: int = Field(ge=0, strict=True)
    call_count: int = Field(ge=0, strict=True)


class DailyUsage(NativeModel):
    date: date
    total_tokens: int = Field(ge=0, strict=True)
    call_count: int = Field(ge=0, strict=True)


class NativeDashboard(NativeModel):
    success: Literal[True] = True
    summary: Summary
    by_model: tuple[ModelUsage, ...] = Field(max_length=100)
    by_workspace: tuple[WorkspaceUsage, ...] = Field(max_length=1)
    daily_trend: tuple[DailyUsage, ...] = Field(max_length=91)

    @model_validator(mode="after")
    def scope_and_totals(self) -> NativeDashboard:
        if any(row.workspace_id != WORKSPACE for row in self.by_workspace):
            raise ValueError("Cross-workspace response")
        if len({row.model for row in self.by_model}) != len(self.by_model):
            raise ValueError("Duplicate model aggregate")
        if len({row.date for row in self.daily_trend}) != len(self.daily_trend):
            raise ValueError("Duplicate daily aggregate")
        for rows in (self.by_model, self.by_workspace, self.daily_trend):
            if (
                sum(row.total_tokens for row in rows) != self.summary.total_tokens
                or sum(row.call_count for row in rows) != self.summary.total_llm_calls
            ):
                raise ValueError("Inconsistent native aggregates")
        # Empty workspace arrays cannot attest scope when there is nonempty usage.
        if (self.summary.total_tokens or self.summary.total_llm_calls) and not self.by_workspace:
            raise ValueError("Missing workspace attribution")
        return self


class UsageSource(Protocol):
    def read(self, period: Period) -> NativeDashboard: ...


class EngineUsageSource:
    def __init__(self) -> None:
        self.slots = BoundedSemaphore(2)

    def read(self, period: Period) -> NativeDashboard:
        if period not in ("7d", "30d", "90d"):
            raise ValueError("Unsupported native period")
        if not self.slots.acquire(blocking=False):
            raise TokenomicsUnavailable("tokenomics_busy")
        try:
            credentials = json.loads((Path.home() / ".agentengine/auth.json").read_text())
            token = credentials["credentials"][BASE]["access_token"]
            request = Request(
                BASE
                + f"/api/v1/projects/{PROJECT}/cost/dashboard"
                + f"?period={period}&workspace_id={WORKSPACE}",
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/vnd.agent-engine-2026-09-20-preview+json",
                },
                method="GET",
            )
            with build_opener(NoRedirect()).open(request, timeout=30) as response:
                body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise TokenomicsUnavailable("tokenomics_response_limit")
            return NativeDashboard.model_validate_json(body)
        except TokenomicsUnavailable:
            raise
        except HTTPError as error:
            code = {
                401: "tokenomics_auth_expired",
                403: "tokenomics_source_denied",
                429: "tokenomics_rate_limited",
            }.get(error.code, "tokenomics_source_unavailable")
            error.close()
            raise TokenomicsUnavailable(code) from None
        except TimeoutError:
            raise TokenomicsUnavailable("tokenomics_timeout") from None
        except ValidationError:
            raise TokenomicsUnavailable("tokenomics_invalid_source") from None
        except Exception:
            raise TokenomicsUnavailable() from None
        finally:
            self.slots.release()


def reviewed_price(model: str) -> Price | None:
    # Exact reviewed model only. Never load the compatibility sample as live usage.
    if model != "gpt-5.6-luna":
        return None
    return Price(
        provider="openai",
        model=model,
        source_url="https://developers.openai.com/api/docs/pricing",
        checked_at=datetime(2026, 11, 2, 1, 3, 15, tzinfo=UTC),
        context_band="short",
        input_per_million=Decimal("0.20"),
        output_per_million=Decimal("1.20"),
    )


class TokenomicsService:
    def __init__(self, source: UsageSource | None) -> None:
        self.source = source

    def dashboard(self, period: Period, *, now: datetime | None = None) -> DashboardView:
        if self.source is None:
            raise TokenomicsUnavailable("tokenomics_not_configured")
        now = now or datetime.now(UTC)
        window = Window(start=now - timedelta(days=int(period[:-1])), end=now)
        data = self.source.read(period)
        if any(row.date < window.start.date() or row.date > now.date() for row in data.daily_trend):
            raise TokenomicsUnavailable("tokenomics_invalid_source")

        def observed(value: int, unit: Unit = "tokens") -> Metric:
            return Metric(
                value=Decimal(value),
                unit=unit,
                basis="observed",
                source=SOURCE,
                scope=SCOPE,
                observed_at=now,
                window=window,
                coverage="partial",
                reason="Native period aggregate; exact boundary/deduplication unverified",
            )

        def missing(unit: Unit, reason: str) -> Metric:
            return Metric(
                value=None,
                unit=unit,
                currency="USD" if unit == "money" else None,
                basis="unavailable",
                source=SOURCE,
                scope=SCOPE,
                observed_at=now,
                window=window,
                coverage="unknown",
                reason=reason,
            )

        unavailable = Section(status="unavailable", reason="Not attributed by native cost source")
        estimate = None
        cost = missing("money", "No verified price/category attribution for this usage")
        if len(data.by_model) == 1 and (price := reviewed_price(data.by_model[0].model)):
            estimate = standard_scenario(
                model=price.model,
                input_tokens=data.summary.total_prompt_tokens,
                output_tokens=data.summary.total_completion_tokens,
                price=price,
            )
            cost = Metric(
                value=estimate.amount_usd,
                unit="money",
                currency="USD",
                basis="estimated",
                source=price.source_url,
                scope=SCOPE,
                observed_at=now,
                window=window,
                coverage="partial",
                reason="Standard uncached scenario; excludes other fees",
            )

        def section(rows: tuple[BreakdownRow, ...]) -> Section:
            return Section(
                status="partial" if rows else "empty",
                rows=rows,
                reason="Native aggregates only; missing observations are not zero",
            )

        return DashboardView(
            kpis=Dashboard(
                total_cost=cost,
                observed_tokens=observed(data.summary.total_tokens),
                average_cost_per_execution=missing("money", "No execution denominator"),
                cache_hit_ratio=missing("ratio", "No eligible retrieval-cache lookup counts"),
                token_goodput=missing("ratio", "No token/outcome attribution"),
                execution_count=missing("executions", "LLM calls are not executions"),
                partial=True,
            ),
            applications=section(
                tuple(
                    BreakdownRow(key=SCOPE, metric=observed(row.total_tokens))
                    for row in data.by_workspace
                )
            ),
            daily=section(
                tuple(
                    BreakdownRow(key=row.date.isoformat(), metric=observed(row.total_tokens))
                    for row in sorted(data.daily_trend, key=lambda row: row.date)
                )
            ),
            anomalies=Section(
                status="unavailable", reason="Complete comparable daily baseline absent"
            ),
            context=unavailable,
            token_categories=section(
                (
                    BreakdownRow(key="input", metric=observed(data.summary.total_prompt_tokens)),
                    BreakdownRow(
                        key="output", metric=observed(data.summary.total_completion_tokens)
                    ),
                    BreakdownRow(
                        key="cached_input", metric=missing("tokens", "Cache split unavailable")
                    ),
                )
            ),
            models=section(
                tuple(
                    BreakdownRow(key=row.model, metric=observed(row.total_tokens))
                    for row in data.by_model
                )
            ),
            agents=unavailable,
            intents=unavailable,
            estimate=estimate,
        )

    def focus(self) -> FocusPage:
        # No native event/SKU/billed-record endpoint. No fabricated records or extra GET.
        return FocusPage(
            status="unavailable", reason="Native source has no billed event/SKU records"
        )
