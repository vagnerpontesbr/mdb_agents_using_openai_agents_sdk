"""Versioned domain boundaries, not a catalog of intents or model authority."""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=False)


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class PrincipalView(Contract):
    user_id: str
    email: str
    role: Role


class LoginRequest(Contract):
    email: str = Field(min_length=1, max_length=254)
    password: SecretStr = Field(min_length=8, max_length=128)


class RegistrationRequest(LoginRequest):
    role: Role = Role.USER


class ErrorResponse(Contract):
    error: str


class RequestInterpretation(Contract):
    """Untrusted model proposal; contains no identity or execution permission."""

    schema_version: Literal[1] = 1
    summary: str = Field(min_length=1, max_length=1000)
    needs_clarification: bool
    clarification: str | None = Field(default=None, max_length=500)


class SpecialistOutcome(Contract):
    schema_version: Literal[1] = 1
    status: Literal["resolved", "needs_information", "needs_approval", "escalate"]
    summary: str = Field(min_length=1, max_length=2000)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=20)


class InvoiceFacts(Contract):
    """Only an authorized business adapter may supply these facts to rendering."""

    invoice_id: str = Field(min_length=1, max_length=100)
    amount_minor: int = Field(ge=0, le=999_999_999, strict=True)
    currency: Literal["USD"] = "USD"
    due_date: date


class ProtectedResponse(Contract):
    template_id: Literal["invoice_total.v1"] = "invoice_total.v1"
    text: str
    source_id: str
