"""Typed HTTP boundary around the existing Phase 0 identity implementation."""

from typing import Any, Protocol, cast

from compatibility.demo_auth.auth import Principal
from compatibility.demo_auth.sessions import SessionAuth

from .contracts import PrincipalView


class IdentityService(Protocol):
    def login(self, email: str, password: str, peer: str) -> tuple[str, Principal]: ...
    def principal(self, token: str) -> Principal: ...
    def register(self, token: str, *, email: str, password: str,
                 role: str = "user") -> Principal: ...
    def logout(self, token: str) -> None: ...
    def avatar(self, token: str) -> bytes | None: ...
    def save_avatar(self, token: str, *, content: bytes | None,
                    expected_revision: int) -> dict[str, Any]: ...
    def profile(self, token: str) -> dict[str, Any]: ...
    def save_profile(self, token: str, *, values: dict[str, Any],
                     expected_revision: int) -> dict[str, Any]: ...


def identity_service(store: object) -> IdentityService:
    # Legacy implementation is covered by tests/demo_auth; this bridge does not
    # create a second identity authority or new storage format.
    return cast(IdentityService, SessionAuth(store))


def public_principal(principal: Principal) -> PrincipalView:
    return PrincipalView.model_validate({
        "user_id": principal.user_id, "email": principal.email, "role": principal.role,
    })
