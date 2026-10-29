"""Server-side opaque login sessions; native Engine approvals are separate."""
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets

from .auth import AccessDenied, Auth, Principal

SESSION_SECONDS = 3600
LOGIN_ATTEMPTS = 8


class RateLimited(Exception):
    pass


def token_digest(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise AccessDenied("Login required")
    return hashlib.sha256(token.encode()).hexdigest()


class SessionAuth:
    def __init__(self, store, clock=None):
        self.store, self.auth = store, Auth(store)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def login(self, email, password, peer):
        now = self.clock()
        window = int(now.timestamp()) // 60
        key = hashlib.sha256(f"{peer}:{window}".encode()).hexdigest()
        expires = datetime.fromtimestamp((window + 1) * 60, timezone.utc)
        # Per-peer limit also covers unknown emails, preventing email rotation bypass.
        if self.store.consume_attempt(key, expires) > LOGIN_ATTEMPTS:
            raise RateLimited("Too many login attempts; try again next minute")
        principal = self.auth.authenticate(email, password)
        token = secrets.token_urlsafe(32)
        self.store.insert_session({"_id": token_digest(token), "email": principal.email,
                                   "user_id": principal.user_id,
                                   "expires_at": now + timedelta(seconds=SESSION_SECONDS)})
        return token, principal

    def principal(self, token):
        session = self.store.get_session(token_digest(token), self.clock())
        if not session:
            raise AccessDenied("Login required")
        user = self.store.get(session["email"])
        if (not user or user.get("active") is not True
                or user.get("user_id") != session["user_id"]
                or user.get("role") not in ("user", "admin")):
            raise AccessDenied("Login required")
        # Re-read role: a revoked/demoted account cannot keep cached admin powers.
        return Principal(user["user_id"], user["_id"], user["role"])

    def register(self, token, *, email, password, role="user"):
        if self.principal(token).role != "admin":
            raise AccessDenied("Administrator required")
        return self.auth._insert(email, password, role)

    def logout(self, token):
        self.store.delete_session(token_digest(token))
