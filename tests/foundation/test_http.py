import asyncio

import pytest
from fastapi.testclient import TestClient

from compatibility.demo_auth.sessions import token_digest
from telecom_app.api import COOKIE, create_app
from telecom_app.config import CONCURRENCY, Settings
from telecom_app.security import Boundary
from tests.foundation.conftest import PASSWORD, URI, login


def test_admin_user_reload_and_logout(client, identity):
    assert client.get("/api/me").status_code == 401
    response = login(client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    token = client.cookies[COOKIE]
    assert token not in repr(identity.store.sessions)
    assert token_digest(token) in identity.store.sessions
    assert client.get("/api/me").json()["role"] == "admin"
    created = client.post("/api/users", json={
        "email": "member@example.test", "password": PASSWORD, "role": "user",
    })
    assert created.status_code == 201
    assert set(created.json()) == {"email", "user_id", "role"}
    assert client.post("/api/users", json={
        "email": "member@example.test", "password": PASSWORD,
    }).status_code == 409
    assert client.post("/api/logout", json={}).status_code == 200
    assert client.get("/api/me", headers={"Cookie": f"{COOKIE}={token}"}).status_code == 401
    assert client.post("/api/login", json={
        "email": "member@example.test", "password": PASSWORD,
    }).status_code == 200
    assert client.post("/api/users", json={
        "email": "denied@example.test", "password": PASSWORD, "role": "admin",
    }).status_code == 403
    assert "denied@example.test" not in identity.store.users


def test_demoted_and_disabled_users_cannot_keep_permissions(client, identity):
    login(client)
    identity.store.users["admin@mongodb.com"]["role"] = "user"
    assert client.post("/api/users", json={
        "email": "denied@example.test", "password": PASSWORD,
    }).status_code == 403
    identity.store.users["admin@mongodb.com"]["active"] = False
    assert client.get("/api/me").status_code == 401


def test_host_origin_size_and_injected_authority_are_rejected(client, identity):
    login(client)
    payload = {"email": "other@example.test", "password": PASSWORD}
    for headers in [{"Host": "attacker.test"}, {"Origin": "https://attacker.test"}]:
        assert client.post("/api/users", json=payload, headers=headers).status_code == 403
    assert client.post("/api/users", json={**payload, "requester_id": "forged"}).status_code == 400
    assert client.post("/api/users", json={**payload, "role": "owner"}).status_code == 400
    assert client.post("/api/login", content=b"x" * 8193,
                       headers={"Content-Type": "application/json"}).status_code == 413
    assert "other@example.test" not in identity.store.users


def test_validation_and_dependency_errors_never_echo_private_input(client, identity):
    result = client.post("/api/login", json={"password": PASSWORD, "extra": "private-marker"})
    assert result.status_code == 400
    assert PASSWORD not in result.text and "private-marker" not in result.text
    def failed(*args):
        raise RuntimeError("private-provider-credential")
    identity.store.get = failed
    result = client.post("/api/login", json={"email": "admin@mongodb.com", "password": PASSWORD})
    assert result.status_code == 503
    assert "private-provider" not in result.text
    assert result.headers["cache-control"] == "no-store"


def test_unknown_accounts_share_peer_rate_limit(client):
    for index in range(8):
        assert client.post("/api/login", json={
            "email": f"missing{index}@example.test", "password": PASSWORD,
        }).status_code == 401
    result = client.post("/api/login", json={"email": "admin@mongodb.com", "password": PASSWORD})
    assert result.status_code == 429 and result.headers["retry-after"] == "60"


def test_client_lifecycle_closes_without_provisioning(monkeypatch):
    class Client:
        closed = False
        def close(self):
            self.closed = True
    client = Client()
    monkeypatch.setattr("telecom_app.api.connect", lambda settings: client)
    def failed(client):
        raise RuntimeError("private-connection-details")
    monkeypatch.setattr("telecom_app.api.verify_connection", failed)
    with pytest.raises(RuntimeError, match="Identity service unavailable") as error:
        with TestClient(create_app(Settings(URI))):
            pass
    assert "private-connection" not in str(error.value)
    assert client.closed


def test_admission_is_bounded_and_released_after_requests():
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        count = 0
        async def endpoint(scope, receive, send):
            nonlocal count
            count += 1
            if count == CONCURRENCY:
                started.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        boundary = Boundary(endpoint, "http://127.0.0.1:8000")
        async def call():
            output = []
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}
            async def send(message):
                output.append(message)
            await boundary({"type": "http", "method": "GET", "headers": [
                (b"host", b"127.0.0.1:8000")], "path": "/"}, receive, send)
            return output[0]["status"]
        tasks = [asyncio.create_task(call()) for _ in range(CONCURRENCY)]
        await asyncio.wait_for(started.wait(), 2)
        try:
            assert await call() == 503
        finally:
            release.set()
            assert await asyncio.gather(*tasks) == [200] * CONCURRENCY
        assert await call() == 200
        assert boundary.active == 0
    asyncio.run(run())
