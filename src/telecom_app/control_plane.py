"""Application-owned settings: immutable request snapshots and atomic revisions."""

from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import Field
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from compatibility.demo_auth.auth import AccessDenied

from .contracts import Contract
from .identity import IdentityService
from .journey import JourneyConflict


class ApplicationLimits(Contract):
    chat_max_chars: int = Field(default=4000, ge=100, le=4000, strict=True)
    knowledge_query_max_chars: int = Field(default=2000, ge=100, le=2000, strict=True)
    library_cache_max_age_seconds: int = Field(default=900, ge=1, le=900, strict=True)


class SettingsChange(ApplicationLimits):
    expected_revision: int = Field(ge=0, strict=True)


class Snapshot(Contract):
    revision: int = Field(default=0, ge=0, strict=True)
    values: ApplicationLimits = ApplicationLimits()


class SettingsStore(Protocol):
    def read(self) -> Snapshot: ...
    def save(self, change: SettingsChange, actor: str) -> Snapshot: ...


class MongoSettingsStore:
    """One fixed document; the last 20 changes are atomically bounded with its values."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        if (collection.database.name != "telecom_identity"
                or collection.name != "application_settings"):
            raise ValueError("Unexpected application settings namespace")
        self.collection = collection

    def read(self) -> Snapshot:
        row = self.collection.find_one({"_id": "application"}, {"revision": 1, "values": 1})
        if row is None:
            return Snapshot()
        return Snapshot.model_validate({key: row[key] for key in ("revision", "values")})

    def save(self, change: SettingsChange, actor: str) -> Snapshot:
        previous = self.read()
        if previous.revision != change.expected_revision:
            raise JourneyConflict("Settings changed; reload before saving")
        values = ApplicationLimits.model_validate(change.model_dump(exclude={"expected_revision"}))
        next_value = Snapshot(revision=previous.revision + 1, values=values)
        event = {"revision": next_value.revision, "actor_id": actor,
                 "at": datetime.now(UTC), "before": previous.values.model_dump(),
                 "after": values.model_dump()}
        try:
            if previous.revision == 0:
                self.collection.insert_one({"_id": "application", **next_value.model_dump(),
                                            "audit": [event]})
            else:
                result = self.collection.update_one(
                    {"_id": "application", "revision": previous.revision},
                    {"$set": next_value.model_dump(),
                     "$push": {"audit": {"$each": [event], "$slice": -20}}},
                )
                if result.matched_count != 1:
                    raise JourneyConflict("Settings changed; reload before saving")
        except DuplicateKeyError:
            raise JourneyConflict("Settings changed; reload before saving") from None
        return next_value


class ControlPlane:
    def __init__(self, identity: IdentityService, store: SettingsStore | None = None) -> None:
        self.identity, self.store = identity, store

    def admin(self, token: str) -> str:
        actor = self.identity.principal(token)
        if actor.role != "admin":
            raise AccessDenied("Administrator required")
        return str(actor.user_id)

    def snapshot(self) -> Snapshot:
        # Disabled deployments preserve their code defaults; configured read failures propagate.
        return self.store.read() if self.store is not None else Snapshot()

    def read(self, token: str) -> dict[str, Any]:
        self.admin(token)
        snapshot = self.snapshot()
        return {**snapshot.model_dump(), "editable": self.store is not None,
                "source": "application_database" if snapshot.revision else "code_defaults",
                "observed_at": datetime.now(UTC).isoformat(),
                "scope": "application_admission_and_library_cache",
                "audit_retained_changes": 20}

    def save(self, token: str, change: SettingsChange) -> dict[str, Any]:
        actor = self.admin(token)
        if self.store is None:
            raise JourneyConflict("Settings persistence is not configured")
        result = self.store.save(change, actor)
        return {**result.model_dump(), "editable": True, "source": "application_database",
                "observed_at": datetime.now(UTC).isoformat(),
                "scope": "application_admission_and_library_cache", "audit_retained_changes": 20}
