"""HTTP side of telecom-turn-v2; durable input stays owned by Engine."""

import json
from typing import Any, cast

from pydantic import Field, field_validator

from .contracts import Contract
from .profile import Locale

PREFIX = "telecom-turn-v2\n"
LOCALES = ("en-US", "pt-BR", "es-ES")


class Turn(Contract):
    locale: Locale
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty message")
        return value

    def wire(self) -> str:
        return PREFIX + json.dumps(self.model_dump(), ensure_ascii=False, separators=(",", ":"))


def validated_locale(value: object) -> Locale:
    if not isinstance(value, str) or value not in LOCALES:
        raise ValueError("Unsupported locale")
    return cast(Locale, value)


def execution_locale(message: object) -> Locale:
    if message is None:
        return "en-US"  # Historical responses may omit the original input.
    if not isinstance(message, str):
        raise ValueError("Invalid original message")
    if not message.startswith(PREFIX):
        return "en-US"
    if len(message) > 25000:
        raise ValueError("Oversized original message")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate turn field")
            result[key] = value
        return result

    return Turn.model_validate(json.loads(message[len(PREFIX):], object_pairs_hook=unique)).locale
