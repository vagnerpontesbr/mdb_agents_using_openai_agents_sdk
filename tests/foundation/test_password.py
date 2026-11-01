from datetime import UTC, datetime

import pytest

from compatibility.demo_auth.auth import AccessDenied, password_hash
from compatibility.demo_auth.sessions import PasswordRejected, RateLimited
from tests.foundation.conftest import PASSWORD, login

NEW = "synthetic-new-password-only"
PAYLOAD = {"current_password": PASSWORD, "new_password": NEW, "confirmation": NEW}


def test_change_invalidates_all_old_sessions_and_requires_new_login(client, identity):
    login(client)
    other_token, _ = identity.login("admin@mongodb.com", PASSWORD, "other-peer")
    old_hash = identity.store.get("admin@mongodb.com")["password_hash"]
    response = client.post("/api/profile/password", json=PAYLOAD)
    assert response.status_code == 200 and response.json()["reauthenticate"] == "required"
    assert PASSWORD not in response.text and NEW not in response.text
    assert client.get("/api/me").status_code == 401
    with pytest.raises(AccessDenied):
        identity.principal(other_token)
    # Invalidation does not depend on physical deletion or TTL timing.
    assert identity.store.sessions
    assert identity.store.get("admin@mongodb.com")["password_hash"] != old_hash
    assert (
        client.post(
            "/api/login", json={"email": "admin@mongodb.com", "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post("/api/login", json={"email": "admin@mongodb.com", "password": NEW}).status_code
        == 200
    )
    assert client.get("/api/me").json()["role"] == "admin"


@pytest.mark.parametrize(
    "changes",
    [
        {"current_password": "wrong-password"},
        {"new_password": "short"},
        {"confirmation": "different-password"},
        {"email": "other@example.test"},
        {"user_id": "other"},
        {"role": "admin"},
    ],
)
def test_wrong_password_policy_and_injected_identity_do_not_change_credentials(
    client, identity, changes
):
    login(client)
    original = identity.store.get("admin@mongodb.com")["password_hash"]
    response = client.post("/api/profile/password", json={**PAYLOAD, **changes})
    assert response.status_code == 400
    assert NEW not in response.text and PASSWORD not in response.text
    assert identity.store.get("admin@mongodb.com")["password_hash"] == original
    assert client.get("/api/me").status_code == 200


def test_password_attempt_limit_is_per_account_across_sessions(identity):
    identity.clock = lambda: datetime(2026, 11, 1, tzinfo=UTC)
    tokens = [identity.login("admin@mongodb.com", PASSWORD, f"peer-{i}")[0] for i in range(2)]
    for attempt in range(5):
        with pytest.raises(PasswordRejected):
            identity.change_password(
                tokens[attempt % 2], current_password="wrong-password", new_password=NEW
            )
    with pytest.raises(RateLimited):
        identity.change_password(tokens[1], current_password=PASSWORD, new_password=NEW)


def test_login_racing_password_change_cannot_issue_a_valid_old_session(identity):
    authenticate = identity.auth.authenticate_versioned

    def raced(email, password):
        snapshot = authenticate(email, password)
        user = identity.store.users[email]
        user["password_hash"] = password_hash(NEW)
        user["credential_version"] = 1
        return snapshot

    identity.auth.authenticate_versioned = raced
    with pytest.raises(AccessDenied):
        identity.login("admin@mongodb.com", PASSWORD, "synthetic-peer")
    assert not identity.store.sessions


def test_compare_and_swap_rejects_a_concurrent_password_replacement(identity):
    token, principal = identity.login("admin@mongodb.com", PASSWORD, "synthetic-peer")
    before = identity.store.get(principal.email)["password_hash"]
    assert identity.store.replace_password(
        principal.email, principal.user_id, before, password_hash(NEW)
    )
    assert not identity.store.replace_password(
        principal.email, principal.user_id, before, password_hash("losing-password")
    )
    with pytest.raises(AccessDenied):
        identity.change_password(token, current_password=NEW, new_password="losing-password")


def test_ordinary_user_changes_only_own_password(client, identity):
    login(client)
    original = identity.store.get("admin@mongodb.com")["password_hash"]
    client.post("/api/users", json={"email": "member@example.test", "password": PASSWORD})
    client.post("/api/logout", json={})
    client.post("/api/login", json={"email": "member@example.test", "password": PASSWORD})
    assert client.post("/api/profile/password", json=PAYLOAD).status_code == 200
    assert identity.store.get("admin@mongodb.com")["password_hash"] == original
    assert identity.auth.authenticate("member@example.test", NEW).role == "user"
