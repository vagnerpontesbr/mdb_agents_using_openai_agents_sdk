"""Email/password identity and admin-only registration, outside model control."""
from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
from typing import Protocol
import uuid

ITERATIONS = 600_000
BOOTSTRAP_EMAIL = "admin@mongodb.com"


class AccessDenied(Exception):
    pass


class UserExists(Exception):
    pass


def normalized_email(email: str) -> str:
    if not isinstance(email, str) or len(email) > 254:
        raise ValueError("Invalid email")
    email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Invalid email")
    return email


def password_hash(password: str, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ValueError("Password must contain 8 to 128 characters")
    salt = secrets.token_bytes(16) if salt is None else salt
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def password_matches(password: str, encoded: str) -> bool:
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        return False
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or rounds != str(ITERATIONS):
            return False
        salt_bytes, digest_bytes = bytes.fromhex(salt), bytes.fromhex(digest)
        if len(salt_bytes) != 16 or len(digest_bytes) != 32:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, ITERATIONS)
        return hmac.compare_digest(candidate, digest_bytes)
    except (ValueError, AttributeError):
        return False


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    role: str


class UserStore(Protocol):
    def get(self, email: str) -> dict | None: ...
    def insert(self, user: dict) -> None: ...


class Auth:
    def __init__(self, store: UserStore):
        self.store = store
        # Unknown users still execute the password KDF for bounded valid inputs.
        self._dummy_hash = password_hash(secrets.token_urlsafe(24))

    def _insert(self, email: str, password: str, role: str) -> Principal:
        if role not in ("user", "admin"):
            raise ValueError("Unknown role")
        email = normalized_email(email)
        user = {"_id": email, "user_id": str(uuid.uuid4()), "role": role,
                "active": True, "password_hash": password_hash(password), "schema_version": 1}
        self.store.insert(user)
        return Principal(user["user_id"], email, role)

    def bootstrap(self, password: str) -> Principal:
        """Privileged installation operation, never expose as an HTTP route.

        Insert-only: repeated/concurrent bootstrap cannot reset an existing user.
        """
        return self._insert(BOOTSTRAP_EMAIL, password, "admin")

    def authenticate(self, email: str, password: str) -> Principal:
        try:
            user = self.store.get(normalized_email(email))
        except ValueError:
            user = None
        valid = password_matches(password, user["password_hash"] if user else self._dummy_hash)
        if (not valid or not user or user.get("active") is not True
                or user.get("role") not in ("user", "admin")):
            raise AccessDenied("Invalid credentials")
        return Principal(user["user_id"], user["_id"], user["role"])

    def register(self, actor_email: str, actor_password: str, *,
                 email: str, password: str, role: str = "user") -> Principal:
        actor = self.authenticate(actor_email, actor_password)
        if actor.role != "admin":
            raise AccessDenied("Administrator required")
        return self._insert(email, password, role)

    def authorize_requester(self, email: str, password: str, *, requester_id: str) -> Principal:
        """requester_id must come from trusted Engine action metadata, never the caller.

        This local check makes no Engine call and does not accept a review decision.
        """
        actor = self.authenticate(email, password)
        if actor.user_id != requester_id:
            raise AccessDenied("Only the original requester may approve")
        return actor
