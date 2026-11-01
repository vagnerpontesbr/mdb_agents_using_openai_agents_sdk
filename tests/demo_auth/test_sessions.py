import copy
from datetime import datetime, timedelta, timezone
import secrets
import unittest

from compatibility.demo_auth.auth import AccessDenied, BOOTSTRAP_EMAIL
from compatibility.demo_auth.sessions import LOGIN_ATTEMPTS, RateLimited, SessionAuth, token_digest
from tests.demo_auth.test_auth import Store


class SessionStore(Store):
    def __init__(self):
        super().__init__()
        self.sessions, self.attempts = {}, {}

    def update_profile(self, email, user_id, expected_revision, values):
        user = self.users.get(email)
        if (not user or user["user_id"] != user_id or user.get("active") is not True
                or user.get("profile_revision", 0) != expected_revision):
            return False
        user.setdefault("profile", {}).update(copy.deepcopy(values))
        user["profile_revision"] = expected_revision + 1
        return True

    def update_avatar(self, email, user_id, expected_revision, content):
        if not self.update_profile(email, user_id, expected_revision, {}):
            return False
        if content is None:
            self.users[email]["profile"].pop("avatar", None)
        else:
            self.users[email]["profile"]["avatar"] = content
        return True

    def insert_session(self, session):
        self.sessions[session["_id"]] = copy.deepcopy(session)

    def get_session(self, digest, now):
        session = self.sessions.get(digest)
        return copy.deepcopy(session) if session and session["expires_at"] > now else None

    def delete_session(self, digest):
        self.sessions.pop(digest, None)

    def consume_attempt(self, key, expires):
        self.attempts[key] = self.attempts.get(key, 0) + 1
        return self.attempts[key]


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 29, tzinfo=timezone.utc)
        self.store = SessionStore()
        self.service = SessionAuth(self.store, lambda: self.now)
        self.password = secrets.token_urlsafe(16)
        self.service.auth.bootstrap(self.password)

    def login(self):
        return self.service.login(BOOTSTRAP_EMAIL, self.password, "127.0.0.1")[0]

    def test_token_hashed_and_expiry_enforced_without_ttl_deletion(self):
        token = self.login()
        self.assertIn(token_digest(token), self.store.sessions)
        self.assertNotIn(token, repr(self.store.sessions))
        self.assertEqual(self.service.principal(token).role, "admin")
        self.now += timedelta(hours=1)
        with self.assertRaises(AccessDenied):
            self.service.principal(token)
        self.assertEqual(len(self.store.sessions), 1)

    def test_logout_revokes_only_target_session(self):
        first, second = self.login(), self.login()
        self.service.logout(first)
        with self.assertRaises(AccessDenied):
            self.service.principal(first)
        self.assertEqual(self.service.principal(second).email, BOOTSTRAP_EMAIL)

    def test_role_is_refreshed_before_admin_write(self):
        token = self.login()
        self.store.users[BOOTSTRAP_EMAIL]["role"] = "user"
        with self.assertRaises(AccessDenied):
            self.service.register(token, email="denied@example.test", password=self.password)
        self.assertNotIn("denied@example.test", self.store.users)
        self.store.users[BOOTSTRAP_EMAIL]["active"] = False
        with self.assertRaises(AccessDenied):
            self.service.principal(token)

    def test_unknown_emails_share_peer_attempt_limit(self):
        for number in range(LOGIN_ATTEMPTS):
            with self.assertRaises(AccessDenied):
                self.service.login(f"missing-{number}@example.test", self.password, "127.0.0.1")
        with self.assertRaises(RateLimited):
            self.login()
        self.now += timedelta(minutes=1)
        self.assertEqual(self.service.principal(self.login()).role, "admin")

    def test_invalid_token_cannot_register(self):
        for token in ("", "a" * 42, "a" * 43, {"role": "admin"}):
            with self.assertRaises(AccessDenied):
                self.service.register(token, email="denied@example.test", password=self.password)


if __name__ == "__main__":
    unittest.main()
