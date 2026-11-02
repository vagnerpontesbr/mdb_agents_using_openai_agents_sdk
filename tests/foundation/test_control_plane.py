"""Admin controls and atomic revisions; no Atlas/provider traffic."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from telecom_app.api import create_app
from telecom_app.config import Settings
from telecom_app.control_plane import (
    ApplicationLimits,
    ControlPlane,
    MongoSettingsStore,
    SettingsChange,
    Snapshot,
)
from telecom_app.journey import JourneyConflict
from tests.foundation.conftest import ORIGIN, PASSWORD, URI, login


class Store:
    def __init__(self):
        self.value = Snapshot()
        self.actors = []

    def read(self):
        return self.value

    def save(self, change, actor):
        if change.expected_revision != self.value.revision:
            raise JourneyConflict()
        self.value = Snapshot(revision=self.value.revision + 1, values=ApplicationLimits(
            **change.model_dump(exclude={"expected_revision"})))
        self.actors.append(actor)
        return self.value


def test_admin_strict_values_stale_revision_and_snapshot(identity):
    store = Store()
    plane = ControlPlane(identity, store)
    with TestClient(create_app(Settings(URI), identity, control=plane),
                    base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        assert client.get("/api/admin/control-plane").status_code == 401
        login(client)
        original = plane.snapshot()
        before = client.get("/api/admin/control-plane").json()
        payload = {**before["values"], "chat_max_chars": 100, "expected_revision": 0}
        assert client.post("/api/admin/control-plane", json=payload).status_code == 200
        assert original.values.chat_max_chars == 4000
        assert plane.snapshot().values.chat_max_chars == 100
        assert client.post("/api/admin/control-plane", json=payload).status_code == 409
        for patch in ({"chat_max_chars": 4001}, {"chat_max_chars": True},
                      {"library_cache_max_age_seconds": 901}, {"secret": "forged"},
                      {"expected_revision": -1}):
            assert client.post("/api/admin/control-plane",
                               json={**payload, **patch}).status_code == 400
        assert len(store.actors) == 1
        assert "password" not in str(before) and "mongodb+srv" not in str(before)
        token = client.cookies["telecom_session"]
        identity.register(token, email="reader@example.test", password=PASSWORD, role="user")
        client.post("/api/logout")
        client.post("/api/login", json={"email": "reader@example.test", "password": PASSWORD})
        assert client.get("/api/admin/control-plane").status_code == 403
        assert client.post("/api/admin/control-plane", json=payload).status_code == 403
        assert client.get("/api/users").status_code == 403


def test_unconfigured_read_only_and_users_paginated(client, identity):
    login(client)
    view = client.get("/api/admin/control-plane").json()
    assert view["editable"] is False and view["source"] == "code_defaults"
    assert view["integration_status"] == "configured_not_health_verified"
    assert client.post("/api/admin/control-plane", json={
        **view["values"], "expected_revision": 0}).status_code == 409
    identity.register(client.cookies["telecom_session"], email="reader@example.test",
                      password=PASSWORD, role="user")
    page = client.get("/api/users?limit=1").json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    last = client.get("/api/users?limit=1&after=" + page["next_cursor"]).json()
    assert len(last["items"]) == 1 and last["next_cursor"] is None
    assert page["items"][0]["user_id"] != last["items"][0]["user_id"]
    assert set(last["items"][0]) == {"user_id", "email", "role"}
    for suffix in ("?limit=51", "?after=bad", "?tenant=other"):
        assert client.get("/api/users" + suffix).status_code == 400


def collection():
    value = Mock()
    value.database.name = "telecom_identity"
    value.name = "application_settings"
    return value


def test_mongo_atomic_revision_bounded_audit_duplicate_initial_write():
    coll = collection()
    coll.find_one.return_value = None
    store = MongoSettingsStore(coll)
    coll.insert_one.side_effect = DuplicateKeyError("competing initialization")
    with pytest.raises(JourneyConflict):
        store.save(SettingsChange(expected_revision=0), "actor")
    coll.find_one.return_value = {"revision": 3, "values": ApplicationLimits().model_dump()}
    coll.update_one.return_value.matched_count = 0
    with pytest.raises(JourneyConflict):
        store.save(SettingsChange(expected_revision=3), "actor")
    query, update = coll.update_one.call_args.args
    assert query == {"_id": "application", "revision": 3}
    assert update["$set"]["revision"] == 4
    assert update["$push"]["audit"]["$slice"] == -20
    assert update["$push"]["audit"]["$each"][0]["actor_id"] == "actor"


def test_configured_store_failure_never_falls_back():
    coll = collection()
    coll.find_one.side_effect = TimeoutError("private provider detail")
    plane = ControlPlane(Mock(), MongoSettingsStore(coll))
    with pytest.raises(TimeoutError):
        plane.snapshot()


def test_changed_limits_apply_to_next_chat_not_admitted_chat(identity):
    from telecom_app.journey import JourneyService

    store = Store()
    handler = Mock(spec=JourneyService)
    handler.turn_locale.return_value = "en-US"

    def send(*args):
        store.save(SettingsChange(expected_revision=0, chat_max_chars=100), "admin")
        return {"status": "completed", "text": "Admitted request", "locale": "en-US"}

    handler.send.side_effect = send
    with TestClient(create_app(Settings(URI), identity, handler,
                               control=ControlPlane(identity, store)),
                    base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        login(client)
        body = {"conversation_id": "00000000-0000-4000-8000-000000000001", "message": "x" * 150}
        response = client.post("/api/journey/chat", json=body)
        assert "Admitted request" in response.text
        assert client.post("/api/journey/chat", json=body).status_code == 400
        handler.send.assert_called_once()


def test_role_inventory_includes_indirect_consumers(monkeypatch):
    from scripts import prepare_control_plane_resources as gate

    def inventory(*args):
        if args[0] == "customDbRoles":
            return [
                {"roleName": gate.ROLE, "inheritedRoles": []},
                {"roleName": "parent", "inheritedRoles": [{"role": gate.ROLE, "db": "admin"}]},
                {"roleName": "ancestor", "inheritedRoles": [{"role": "parent", "db": "admin"}]},
            ]
        return {"results": [{"username": "indirect", "roles": [{"roleName": "ancestor"}],
                             "scopes": []}]}

    monkeypatch.setattr(gate, "atlas", inventory)
    consumers, roles = gate.role_consumers()
    assert consumers == [{"username": "indirect", "scopes": []}]
    assert set(roles) == {gate.ROLE, "parent", "ancestor"}


def test_resource_preflight_never_writes_without_apply_flag(monkeypatch):
    import json
    from pathlib import Path
    from unittest.mock import MagicMock

    monkeypatch.syspath_prepend("scripts")
    from scripts import apply_control_plane_resources as gate

    proposal = json.loads(Path("compatibility/ui3-control-plane-proposal.json").read_text())
    connection = MagicMock()
    database = connection.__enter__.return_value.telecom_identity
    database.list_collection_names.return_value = []
    monkeypatch.setenv("MONGODB_URI", URI)
    monkeypatch.setattr(gate, "atlas", lambda *args: proposal["role_before"])
    monkeypatch.setattr(gate, "role_consumers",
                        lambda: (proposal["role_consumers"], proposal["affected_role_names"]))
    monkeypatch.setattr(gate, "connect", lambda settings: connection)
    monkeypatch.setattr("sys.argv", ["preflight"])
    gate.main()
    database.command.assert_not_called()
    monkeypatch.setattr(gate, "atlas", lambda *args: {})
    with pytest.raises(ValueError, match="Role drift"):
        gate.main()
    database.command.assert_not_called()
