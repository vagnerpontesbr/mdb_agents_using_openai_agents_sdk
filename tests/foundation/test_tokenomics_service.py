"""Read-only adapter and HTTP authorization contracts using synthetic native data."""

import io
import json
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from compatibility.demo_auth.engine import BASE, PROJECT, WORKSPACE
from telecom_app.api import create_app
from telecom_app.config import Settings
from telecom_app.tokenomics_service import (
    EngineUsageSource,
    NativeDashboard,
    TokenomicsService,
    TokenomicsUnavailable,
)
from tests.foundation.conftest import ORIGIN, PASSWORD, URI, login

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


def native():
    return {
        "summary": {
            "total_tokens": 30,
            "total_prompt_tokens": 20,
            "total_completion_tokens": 10,
            "total_llm_calls": 2,
            "unpriced_llm_calls": 2,
            "total_cost_usd": 0,
        },
        "by_model": [{"model": "gpt-5.6-luna", "total_tokens": 30, "call_count": 2}],
        "by_workspace": [{"workspace_id": WORKSPACE, "total_tokens": 30, "call_count": 2}],
        "daily_trend": [{"date": "2026-11-01", "total_tokens": 30, "call_count": 2}],
        "messages": "PRIVATE_CONVERSATION_SENTINEL",
        "secret": "PRIVATE_SECRET_SENTINEL",
    }


def source(data=None):
    result = Mock()
    result.read.return_value = NativeDashboard.model_validate(data or native())
    return result


def test_projection_never_treats_native_zero_as_billed_or_exposes_content():
    upstream = source()
    result = TokenomicsService(upstream).dashboard("7d", now=NOW)
    upstream.read.assert_called_once_with("7d")
    assert result.kpis.observed_tokens.value == 30
    assert result.kpis.total_cost.value == Decimal("0.000016")
    assert result.kpis.total_cost.basis == "estimated"
    assert result.kpis.total_cost.coverage == "partial"
    assert result.kpis.execution_count.value is None
    assert result.kpis.token_goodput.value is None
    assert result.estimate.assumptions
    assert result.daily.rows[0].key == "2026-11-01"
    assert result.anomalies.status == "unavailable"
    assert "PRIVATE" not in result.model_dump_json()
    assert WORKSPACE not in result.model_dump_json()


def test_unknown_and_multiple_models_never_borrow_price_or_split():
    payload = native()
    payload["by_model"][0]["model"] = "unknown-model"
    assert TokenomicsService(source(payload)).dashboard("7d", now=NOW).kpis.total_cost.value is None
    payload["by_model"] = [
        {"model": "gpt-5.6-luna", "total_tokens": 15, "call_count": 1},
        {"model": "unknown-model", "total_tokens": 15, "call_count": 1},
    ]
    result = TokenomicsService(source(payload)).dashboard("7d", now=NOW)
    assert len(result.models.rows) == 2
    assert result.estimate is None


def test_empty_usage_is_not_fabricated_free_bill():
    payload = native()
    payload["summary"] = dict.fromkeys(payload["summary"], 0)
    for key in ("by_model", "by_workspace", "daily_trend"):
        payload[key] = []
    result = TokenomicsService(source(payload)).dashboard("30d", now=NOW)
    assert result.kpis.observed_tokens.value == 0
    assert result.kpis.total_cost.value is None
    assert result.models.status == "empty"


@pytest.mark.parametrize(
    "kind",
    [
        "cross_scope",
        "duplicate_model",
        "duplicate_day",
        "mismatch",
        "negative",
        "bool",
        "missing_scope",
        "oversized",
        "success_false",
        "invalid_model",
        "partial_categories",
    ],
)
def test_invalid_native_payload_rejected(kind):
    payload = native()
    if kind == "cross_scope":
        payload["by_workspace"][0]["workspace_id"] = "other-workspace"
    elif kind == "duplicate_model":
        payload["by_model"] *= 2
    elif kind == "duplicate_day":
        payload["daily_trend"] *= 2
    elif kind == "mismatch":
        payload["daily_trend"][0]["total_tokens"] = 31
    elif kind == "negative":
        payload["summary"]["total_prompt_tokens"] = -1
    elif kind == "bool":
        payload["summary"]["total_llm_calls"] = True
    elif kind == "missing_scope":
        payload["by_workspace"] = []
    elif kind == "oversized":
        payload["by_model"] *= 101
    elif kind == "success_false":
        payload["success"] = False
    elif kind == "invalid_model":
        payload["by_model"][0]["model"] = "https://private.example/secret"
    else:
        del payload["summary"]["total_prompt_tokens"]
    with pytest.raises(ValidationError):
        NativeDashboard.model_validate(payload)


def test_daily_window_rejects_stale_or_future_data():
    for day in ("2025-01-01", "2027-01-01"):
        payload = native()
        payload["daily_trend"][0]["date"] = day
        with pytest.raises(TokenomicsUnavailable, match="invalid_source"):
            TokenomicsService(source(payload)).dashboard("7d", now=NOW)


def transport(monkeypatch, body=None, error=None):
    monkeypatch.setattr(
        "telecom_app.tokenomics_service.Path.read_text",
        lambda _: json.dumps({"credentials": {BASE: {"access_token": "synthetic-token"}}}),
    )
    opener = Mock()
    if error:
        opener.open.side_effect = error
    else:
        opener.open.return_value.__enter__ = Mock(
            return_value=io.BytesIO(body if body is not None else json.dumps(native()).encode())
        )
        opener.open.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr("telecom_app.tokenomics_service.build_opener", lambda _: opener)
    return opener


def test_transport_exact_get_scope_timeout_and_single_call(monkeypatch):
    opener = transport(monkeypatch)
    result = EngineUsageSource().read("7d")
    assert result.summary.total_tokens == 30
    request = opener.open.call_args.args[0]
    assert request.get_method() == "GET" and request.data is None
    assert request.full_url == (
        BASE + f"/api/v1/projects/{PROJECT}/cost/dashboard" + f"?period=7d&workspace_id={WORKSPACE}"
    )
    assert opener.open.call_args.kwargs == {"timeout": 30}
    assert opener.open.call_count == 1


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "auth_expired"),
        (403, "source_denied"),
        (429, "rate_limited"),
        (500, "source_unavailable"),
        (302, "source_unavailable"),
    ],
)
def test_native_http_failures_are_sanitized_and_not_retried(monkeypatch, status, code):
    opener = transport(
        monkeypatch, error=HTTPError("secret-url", status, "PRIVATE", {}, io.BytesIO(b"PRIVATE"))
    )
    with pytest.raises(TokenomicsUnavailable) as caught:
        EngineUsageSource().read("7d")
    assert caught.value.code == "tokenomics_" + code
    assert "PRIVATE" not in str(caught.value)
    assert opener.open.call_count == 1


@pytest.mark.parametrize(
    "body,error,code",
    [
        (b"x" * 1000001, None, "response_limit"),
        (b"{", None, "invalid_source"),
        (None, TimeoutError("PRIVATE"), "timeout"),
        (None, URLError("PRIVATE"), "source_unavailable"),
    ],
)
def test_transport_limits_timeout_and_invalid_body(monkeypatch, body, error, code):
    opener = transport(monkeypatch, body, error)
    with pytest.raises(TokenomicsUnavailable, match="tokenomics_" + code):
        EngineUsageSource().read("7d")
    assert opener.open.call_count == 1


def test_no_waiting_queue_and_slots_released_after_failure(monkeypatch):
    opener = transport(monkeypatch, error=TimeoutError())
    adapter = EngineUsageSource()
    assert adapter.slots.acquire(False) and adapter.slots.acquire(False)
    with pytest.raises(TokenomicsUnavailable, match="busy"):
        adapter.read("7d")
    opener.open.assert_not_called()
    adapter.slots.release()
    for _ in range(2):
        with pytest.raises(TokenomicsUnavailable, match="timeout"):
            adapter.read("7d")
    assert opener.open.call_count == 2
    adapter.slots.release()


@pytest.fixture
def http(identity):
    upstream = source()
    # HTTP uses current time; keep the synthetic date inside its window.
    payload = native()
    payload["daily_trend"][0]["date"] = datetime.now(UTC).date().isoformat()
    upstream.read.return_value = NativeDashboard.model_validate(payload)
    service = TokenomicsService(upstream)
    with TestClient(
        create_app(Settings(URI), identity, tokenomics=service),
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
    ) as client:
        yield client, upstream


BASE_PATH = "/api/admin/tokenomics/"


def test_admin_authorization_before_any_upstream_call(http, identity):
    client, upstream = http
    for path in ("dashboard", "focus-records"):
        assert client.get(BASE_PATH + path).status_code == 401
    upstream.read.assert_not_called()
    login(client)
    identity.register(
        client.cookies["telecom_session"],
        email="reader@example.test",
        password=PASSWORD,
        role="user",
    )
    client.post("/api/logout")
    client.post("/api/login", json={"email": "reader@example.test", "password": PASSWORD})
    for path in ("dashboard", "focus-records"):
        assert client.get(BASE_PATH + path).status_code == 403
    upstream.read.assert_not_called()


@pytest.mark.parametrize(
    "query",
    [
        "workspace_id=other",
        "project_id=other",
        "period=0d",
        "period=91d",
        "period=7d&period=30d",
        "start=2026-01-01",
        "end=2026-01-02",
        "secret=PRIVATE",
        "limit=101",
        "cursor=x",
    ],
)
def test_filters_and_client_scope_overrides_fail_before_read(http, query):
    client, upstream = http
    login(client)
    assert client.get(BASE_PATH + "dashboard?" + query).status_code == 400
    upstream.read.assert_not_called()


def test_admin_periods_no_inference_and_focus_is_explicitly_unavailable(http):
    client, upstream = http
    login(client)
    upstream.read.assert_not_called()  # startup/login do not read Engine
    for period in ("7d", "30d", "90d"):
        response = client.get(BASE_PATH + "dashboard?period=" + period)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["kpis"]["total_cost"]["basis"] == "estimated"
        assert "PRIVATE" not in response.text
    assert [call.args for call in upstream.read.call_args_list] == [("7d",), ("30d",), ("90d",)]
    response = client.get(BASE_PATH + "focus-records?limit=100")
    assert response.status_code == 200
    assert response.json()["records"] == []
    assert response.json()["status"] == "unavailable"
    for suffix in ("?limit=101", "?limit=0", "?limit=-1", "?cursor=abc", "?limit=1&limit=2"):
        assert client.get(BASE_PATH + "focus-records" + suffix).status_code == 400
    assert upstream.read.call_count == 3


@pytest.mark.parametrize(
    "code,status",
    [
        ("tokenomics_rate_limited", 429),
        ("tokenomics_auth_expired", 503),
        ("tokenomics_timeout", 503),
    ],
)
def test_upstream_failures_do_not_clear_application_login_or_leak(http, code, status):
    client, upstream = http
    login(client)
    upstream.read.side_effect = TokenomicsUnavailable(code)
    response = client.get(BASE_PATH + "dashboard")
    assert response.status_code == status
    assert response.json() == {"error": "Tokenomics unavailable", "code": code}
    assert client.get("/api/me").status_code == 200
    assert upstream.read.call_count == 1


def test_revoked_admin_during_read_cannot_receive_response(http, identity):
    client, upstream = http
    login(client)
    token = client.cookies["telecom_session"]
    payload = deepcopy(upstream.read.return_value)

    def revoke(period):
        identity.logout(token)
        return payload

    upstream.read.side_effect = revoke
    assert client.get(BASE_PATH + "dashboard").status_code == 401
    assert upstream.read.call_count == 1


def test_unconfigured_deployment_does_not_consult_cli_credentials(client):
    login(client)
    response = client.get(BASE_PATH + "dashboard")
    assert response.status_code == 503
    assert response.json()["code"] == "tokenomics_not_configured"


def test_explicit_dates_explain_unsupported_source_without_read(http):
    client, upstream = http
    login(client)
    response = client.get(BASE_PATH + "dashboard?start=2026-01-01&end=2026-01-08")
    assert response.status_code == 400
    assert response.json()["code"] == "tokenomics_range_unsupported"
    upstream.read.assert_not_called()


def test_packaged_rate_matches_reviewed_official_snapshot():
    from pathlib import Path

    from telecom_app.tokenomics_service import reviewed_price

    snapshot = json.loads(Path("compatibility/tok0-pricing-sources.json").read_text())
    row = snapshot["observed_model_rates"][0]
    price = reviewed_price(row["model"])
    assert price.input_per_million == Decimal(row["short_context"]["input"])
    assert price.output_per_million == Decimal(row["short_context"]["output"])
    assert price.source_url == snapshot["sources"][row["provider"]]["url"]
