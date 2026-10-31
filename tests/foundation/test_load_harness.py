"""The load fixture must retain real API scope checks and fail closed on SSE errors."""

import base64
import io
import json
import sqlite3
import wave
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.load.http_fixture import application


@pytest.fixture
def load_client(tmp_path, monkeypatch):
    state = tmp_path / "engine-double.sqlite"
    with sqlite3.connect(state) as store:
        store.execute(
            "CREATE TABLE executions (id TEXT PRIMARY KEY, session TEXT, body TEXT)"
        )
    monkeypatch.setenv("TELECOM_LOAD_FIXTURE", "isolated-mock-v1")
    monkeypatch.setenv("TELECOM_LOAD_STATE", str(state))
    monkeypatch.setenv("TELECOM_LOAD_ORIGIN", "http://127.0.0.1:53190")
    monkeypatch.setenv("TELECOM_LOAD_VOICE", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APP_KNOWLEDGE_ENABLED", raising=False)
    with TestClient(application(), base_url="http://127.0.0.1:53190") as client:
        yield client


def headers(actor="load-a"):
    return {"Origin": "http://127.0.0.1:53190", "Cookie": "telecom_session=" + actor}


def test_load_fixture_keeps_api_identity_and_recovery_boundaries(load_client):
    conversation = str(uuid4())
    response = load_client.post(
        "/api/journey/chat",
        headers=headers(),
        json={
            "conversation_id": conversation,
            "message": "synthetic load",
        },
    )
    assert response.status_code == 200
    result = json.loads(response.text.split("event: result\ndata: ")[1].strip())
    recovered = load_client.post(
        "/api/journey/latest", headers=headers(), json={"conversation_id": conversation}
    )
    assert recovered.json() == result
    denied = load_client.post(
        "/api/journey/status",
        headers=headers("load-b"),
        json={"execution_id": result["execution_id"]},
    )
    assert denied.status_code == 403
    unrelated = load_client.post(
        "/api/journey/latest",
        headers=headers("load-b"),
        json={"conversation_id": conversation},
    )
    assert unrelated.json() == {"status": "empty"}


def test_load_fixture_failure_is_an_uncertain_event_not_a_success(load_client):
    response = load_client.post(
        "/api/journey/chat",
        headers=headers(),
        json={
            "conversation_id": str(uuid4()),
            "message": "injected-unavailable",
        },
    )
    assert response.status_code == 200
    assert "event: error\n" in response.text
    assert "event: result\n" not in response.text
    assert "Synthetic transport response." not in response.text


def test_load_fixture_requires_explicit_enable(monkeypatch):
    monkeypatch.delenv("TELECOM_LOAD_FIXTURE", raising=False)
    with pytest.raises(RuntimeError, match="Explicit load fixture required"):
        application()


def test_voice_transport_retains_pcm_validation_and_execution_scope(load_client):
    response = load_client.post("/api/voice/transcribe", headers=headers(),
                                json={"pcm_base64": "not audio"})
    assert response.status_code == 400
    encoded = base64.b64encode(b"\x00\x04\x00\xfc" * 3000).decode()
    response = load_client.post("/api/voice/transcribe", headers=headers(),
                                json={"pcm_base64": encoded})
    assert response.json() == {"text": "Synthetic transport request."}
    response = load_client.post("/api/journey/chat", headers=headers(),
                                json={"conversation_id": str(uuid4()), "message": "voice"})
    result = json.loads(response.text.split("event: result\ndata: ")[1].strip())
    body = {"execution_id": result["execution_id"]}
    assert load_client.post("/api/voice/speak", headers=headers("load-b"),
                            json=body).status_code == 403
    response = load_client.post("/api/voice/speak", headers=headers(), json=body)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(response.content), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                wav.getnframes()) == (1, 2, 24000, 6000)
