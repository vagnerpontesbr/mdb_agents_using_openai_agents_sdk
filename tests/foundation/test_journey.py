"""Authenticated journey boundary; synthetic Engine transport, no hosted claims."""

import base64
import copy
import json
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from compatibility.demo_auth.auth import AccessDenied
from telecom_app.api import COOKIE, create_app
from telecom_app.config import Settings
from telecom_app.journey import (
    ORG,
    PROJECT,
    WORKSPACE,
    EngineAPI,
    EngineUnavailable,
    JourneyConflict,
    JourneyService,
    session_id,
)
from telecom_app.voice import MAX_PCM, pcm_bytes
from tests.foundation.conftest import ORIGIN, PASSWORD, URI, login


@pytest.fixture
def journey(identity):
    token, actor = identity.login("admin@mongodb.com", PASSWORD, "synthetic")
    conversation, execution = uuid4(), str(uuid4())
    engine = Mock(spec=EngineAPI)
    row = {
        "execution_id": execution,
        "user_id": actor.user_id,
        "org_id": ORG,
        "project_id": PROJECT,
        "workspace_id": WORKSPACE,
        "session_id": session_id(actor.user_id, conversation),
        "status": "completed",
        "result": json.dumps(
            {
                "contract": "telecom-journey-v1",
                "text": "Verified fixture.",
                "status": "completed",
                "specialists": ["financial"],
            }
        ),
    }
    engine.execution.side_effect = lambda value: copy.deepcopy(row)
    engine.invoke.return_value = {"execution_id": execution}
    engine.latest.return_value = execution
    return JourneyService(identity, engine), engine, row, token, conversation


def pending(row):
    row.update(
        status="suspended",
        suspend_generation=1,
        suspend_context={
            "interrupts": [
                {
                    "id": "review-id",
                    "value": {
                        "contract": "openai-engine-review-v2",
                        "requesting_user_id": row["user_id"],
                        "allowed_decisions": ["approve", "reject"],
                        "action": {
                            "tool_name": "telco_simulate_plan_change",
                            "tool_call_id": "journey-plan-change",
                            "arguments": {
                                "plan_id": "fiber-500",
                                "monthly_minor": 8990,
                                "proposal_id": "a" * 64,
                            },
                        },
                    },
                }
            ]
        },
    )


def test_send_binds_identity_session_and_recovers_native_execution(journey):
    service, engine, row, token, conversation = journey
    result = service.send(token, conversation, "Read demo-1")
    assert result["text"] == "Verified fixture."
    engine.invoke.assert_called_once_with(row["user_id"], row["session_id"], "Read demo-1")
    assert service.latest(token, conversation) == result


@pytest.mark.parametrize(
    "field", ["user_id", "org_id", "project_id", "workspace_id", "execution_id", "session_id"]
)
def test_other_scope_cannot_read_or_approve(journey, field):
    service, engine, row, token, _ = journey
    identifier = row["execution_id"]
    pending(row)
    row[field] = str(uuid4())
    with pytest.raises(AccessDenied):
        service.decide(token, identifier, "a" * 64, "approve")
    engine.resume.assert_not_called()


def test_another_admin_cannot_approve_requester_action(journey, identity):
    service, engine, row, token, _ = journey
    pending(row)
    identity.register(token, email="second@example.test", password=PASSWORD, role="admin")
    second, _ = identity.login("second@example.test", PASSWORD, "second")
    with pytest.raises(AccessDenied):
        service.present(second, row["execution_id"])
    engine.resume.assert_not_called()


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_review_pins_exact_native_generation(journey, decision):
    service, engine, row, token, _ = journey
    pending(row)
    shown = service.present(token, row["execution_id"])
    service.decide(token, row["execution_id"], shown["action_digest"], decision)
    engine.resume.assert_called_once_with(row["execution_id"], 1, decision)
    engine.resume.reset_mock()
    row["suspend_generation"] = 2
    with pytest.raises(JourneyConflict):
        service.decide(token, row["execution_id"], shown["action_digest"], decision)
    engine.resume.assert_not_called()


def test_changed_price_invalidates_approval(journey):
    service, engine, row, token, _ = journey
    pending(row)
    shown = service.present(token, row["execution_id"])
    row["suspend_context"]["interrupts"][0]["value"]["action"]["arguments"]["monthly_minor"] = 10990
    with pytest.raises(JourneyConflict):
        service.decide(token, row["execution_id"], shown["action_digest"], "approve")
    engine.resume.assert_not_called()


def test_unknown_deployment_and_uncertain_invoke_never_report_success(journey):
    service, engine, row, token, conversation = journey
    row["result"] = {"response": "unrecognized result"}
    with pytest.raises((ValueError, EngineUnavailable)):
        service.present(token, row["execution_id"])
    engine.invoke.side_effect = EngineUnavailable()
    with pytest.raises(EngineUnavailable):
        service.send(token, conversation, "x")
    engine.invoke.assert_called_once()


def test_native_transport_uses_session_header_and_atomic_generation():
    api = EngineAPI()
    api.call = Mock(return_value={})
    api.invoke("trusted", "session", "hello")
    args = api.call.call_args.args
    assert args[1] == {"user_id": "trusted", "message": "hello"}
    assert args[2]["X-Session-ID"] == "session"
    api.resume("execution", 7, "approve")
    assert api.call.call_args.args[1] == {"decision": "approved", "suspend_generation": 7}


def test_journey_http_requires_login_and_rejects_forged_identity(identity, journey):
    service, engine, row, _, conversation = journey
    with TestClient(
        create_app(Settings(URI), identity, service), base_url=ORIGIN, headers={"Origin": ORIGIN}
    ) as client:
        assert client.get("/api/capabilities").status_code == 401
        assert (
            client.post(
                "/api/journey/chat",
                json={"conversation_id": str(conversation), "message": "demo-1"},
            ).status_code
            == 401
        )
        login(client)
        assert client.get("/api/capabilities").json()["journey"]
        assert (
            client.post(
                "/api/journey/chat",
                json={
                    "conversation_id": str(conversation),
                    "message": "demo-1",
                    "user_id": "forged",
                },
            ).status_code
            == 400
        )
        result = client.post(
            "/api/journey/chat",
            json={"conversation_id": str(conversation), "message": "Read demo-1"},
        )
        assert result.status_code == 200
        assert "event: progress" in result.text and "Verified fixture." in result.text
        assert (
            client.post(
                "/api/voice/speak", json={"execution_id": row["execution_id"], "text": "injected"}
            ).status_code
            == 400
        )
        identity.logout(client.cookies[COOKIE])
        assert (
            client.post(
                "/api/journey/status", json={"execution_id": row["execution_id"]}
            ).status_code
            == 401
        )
    engine.resume.assert_not_called()


@pytest.mark.parametrize("pcm", [b"", b"\x01", bytes(12000), b"\x00\x10" * 100, bytes(MAX_PCM + 2)])
def test_invalid_or_silent_pcm_never_reaches_provider(pcm):
    with pytest.raises(ValueError):
        pcm_bytes(base64.b64encode(pcm).decode())


def test_pcm_is_little_endian_and_bounded():
    pcm = b"\x00\x10" * 6000
    assert pcm_bytes(base64.b64encode(pcm).decode()) == pcm
    with pytest.raises(ValueError):
        pcm_bytes("not valid base64!")
