"""Bounded own-profile contracts; identity and authorization never come from preferences."""

import unicodedata
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from .contracts import Contract, PrincipalView

Locale = Literal["en-US", "pt-BR", "es-ES"]


class ProfileInput(Contract):
    display_name: str = Field(min_length=1, max_length=80)
    timezone: str = Field(min_length=1, max_length=100)
    locale: Locale
    expected_revision: int = Field(ge=0, le=2_147_483_646, strict=True)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(unicodedata.category(char).startswith("C") for char in value):
            raise ValueError("Invalid display name")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("Invalid timezone") from None
        return value


class ProfileView(PrincipalView):
    display_name: str
    timezone: str
    locale: Locale
    revision: int
    has_avatar: bool = False
