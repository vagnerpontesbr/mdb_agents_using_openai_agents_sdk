"""Authenticated journey boundary; synthetic Engine transport, no hosted claims."""

import base64
import copy
import json
from unittest.mock import AsyncMock, Mock
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


def test_recovery_uses_authenticated_user_even_with_same_conversation_uuid(journey, identity):
    service, engine, row, token, conversation = journey
    identity.register(token, email="recovery@example.test", password=PASSWORD, role="user")
    other_token, other = identity.login("recovery@example.test", PASSWORD, "other")
    with pytest.raises(AccessDenied):
        service.latest(other_token, conversation)
    engine.latest.assert_called_once_with(session_id(other.user_id, conversation))
    assert session_id(other.user_id, conversation) != row["session_id"]
    engine.invoke.assert_not_called()
    engine.resume.assert_not_called()


def test_recovery_rejects_another_conversation_of_same_user(journey):
    service, engine, row, token, _ = journey
    with pytest.raises(JourneyConflict):
        service.latest(token, uuid4())
    engine.invoke.assert_not_called()
    engine.resume.assert_not_called()


def test_recreated_service_recovers_engine_review_without_local_run_state(journey):
    service, engine, row, token, conversation = journey
    pending(row)
    expected = service.latest(token, conversation)
    restarted = JourneyService(service.identity, engine)
    assert restarted.latest(token, conversation) == expected
    engine.invoke.assert_not_called()
    engine.resume.assert_not_called()


def test_localized_turn_snapshots_profile_and_recovers_without_rereading_it(journey):
    from telecom_app.turn_locale import Turn

    service, engine, row, token, conversation = journey
    service.localized_turns = True
    profile = service.identity.profile(token)
    service.identity.save_profile(token, values={"display_name": "Synthetic", "timezone": "UTC",
                                  "locale": "pt-BR"}, expected_revision=profile["revision"])
    captured = service.turn_locale(token)
    profile = service.identity.profile(token)
    service.identity.save_profile(token, values={"display_name": "Synthetic", "timezone": "UTC",
                                  "locale": "es-ES"}, expected_revision=profile["revision"])
    row["message"] = Turn(locale="pt-BR", message="fatura demo-1").wire()
    row["result"] = json.dumps({"contract": "telecom-journey-v1", "text": "Fatura sintética.",
                               "status": "completed", "specialists": ["financial"],
                               "locale": "pt-BR"})
    result = service.send(token, conversation, "fatura demo-1", captured)
    engine.invoke.assert_called_once_with(row["user_id"], row["session_id"], row["message"])
    assert result["locale"] == "pt-BR"
    restarted = JourneyService(service.identity, engine, localized_turns=True)
    assert restarted.latest(token, conversation)["locale"] == "pt-BR"
    assert restarted.turn_locale(token) == "es-ES"


def test_localized_review_preserves_digest_after_profile_change(journey):
    from telecom_app.turn_locale import Turn

    service, engine, row, token, _ = journey
    pending(row)
    row["message"] = Turn(locale="pt-BR", message="Simule fiber-500").wire()
    shown = service.present(token, row["execution_id"])
    assert shown["locale"] == "pt-BR"
    profile = service.identity.profile(token)
    service.identity.save_profile(token, values={"display_name": "Synthetic", "timezone": "UTC",
                                  "locale": "es-ES"}, expected_revision=profile["revision"])
    assert service.present(token, row["execution_id"])["action_digest"] == shown["action_digest"]
    service.decide(token, row["execution_id"], shown["action_digest"], "reject")
    engine.resume.assert_called_once_with(row["execution_id"], 1, "reject")


@pytest.mark.parametrize("locale", ["fr-FR", None, [], True])
def test_invalid_hosted_locale_never_becomes_public_result(journey, locale):
    service, _, row, token, _ = journey
    result = json.loads(row["result"])
    result["locale"] = locale
    row["result"] = json.dumps(result)
    with pytest.raises(EngineUnavailable):
        service.present(token, row["execution_id"])


def test_result_cannot_change_original_turn_language(journey):
    from telecom_app.turn_locale import Turn

    service, _, row, token, _ = journey
    row["message"] = Turn(locale="pt-BR", message="fatura").wire()
    with pytest.raises(EngineUnavailable, match="locale mismatch"):
        service.present(token, row["execution_id"])


def test_localized_invocation_requires_native_input_roundtrip(journey):
    service, engine, _, token, conversation = journey
    service.localized_turns = True
    with pytest.raises(JourneyConflict, match="Invocation message mismatch"):
        service.send(token, conversation, "demo-1")
    engine.invoke.assert_called_once()


@pytest.mark.parametrize("locale", ["en-US", "pt-BR", "es-ES"])
def test_audio_locale_survives_profile_change_and_tts_uses_execution(identity, journey, locale):
    from telecom_app.turn_locale import Turn
    from telecom_app.voice import VoiceService

    service, engine, row, _, conversation = journey
    service.localized_turns = True
    speech = Mock(spec=VoiceService)
    speech.transcribe = AsyncMock(return_value="Read demo-1")
    speech.speak = AsyncMock(return_value=b"synthetic WAV")
    app = create_app(Settings(URI), identity, service)
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        app.state.voice = speech
        body = {"pcm_base64": "synthetic", "locale": locale}
        assert client.post("/api/voice/transcribe", json=body).status_code == 401
        speech.transcribe.assert_not_called()
        login(client)
        assert client.post("/api/voice/transcribe", json=body).json() == {
            "text": "Read demo-1", "locale": locale}
        speech.transcribe.assert_awaited_once_with("synthetic", locale)
        wire = Turn(locale=locale, message="Read demo-1").wire()
        row["message"] = wire
        result = json.loads(row["result"])
        result["locale"] = locale
        row["result"] = json.dumps(result)
        # Profile remains English; voice snapshot is independent presentation context.
        response = client.post("/api/journey/chat", json={
            "conversation_id": str(conversation), "message": "Read demo-1", "audio_locale": locale})
        assert "event: result" in response.text
        assert engine.invoke.call_args.args[-1] == wire
        response = client.post("/api/voice/speak", json={"execution_id": row["execution_id"]})
        assert response.status_code == 200 and response.headers["Content-Language"] == locale
        speech.speak.assert_awaited_once_with("Verified fixture.", locale)
        row["user_id"] = "other"
        assert client.post("/api/voice/speak", json={
            "execution_id": row["execution_id"]}).status_code == 403
        assert speech.speak.await_count == 1
        for path, invalid in [
            ("/api/voice/transcribe", {**body, "locale": "fr-FR"}),
            ("/api/journey/chat", {"conversation_id": str(conversation),
                                    "message": "x", "audio_locale": "fr-FR"}),
        ]:
            assert client.post(path, json=invalid).status_code == 400
        service.localized_turns = False
        assert client.post("/api/voice/transcribe", json={
            **body, "locale": "pt-BR"}).status_code == 409
        assert client.post("/api/journey/chat", json={
            "conversation_id": str(conversation), "message": "x", "audio_locale": "pt-BR"
        }).status_code == 409
        assert speech.transcribe.await_count == 1
