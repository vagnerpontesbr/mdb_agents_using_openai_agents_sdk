"""Authoritative read-side governance backed by native-bound publication evidence."""

import hashlib
import json
from typing import Any

from bson.codec_options import CodecOptions
from pymongo.database import Database

from .knowledge import Version


def version_key(version: Version) -> str:
    return hashlib.sha256(
        json.dumps(
            [version.tenant_id, version.document_id, version.version_id, version.revision]
        ).encode()
    ).hexdigest()


def document_key(tenant: str, document: str) -> str:
    return hashlib.sha256(json.dumps([tenant, document]).encode()).hexdigest()


class MongoKnowledgeAuthority:
    def __init__(self, database: Database[dict[str, Any]], *,
                 load_environment: bool = False) -> None:
        expected = "telecom_load_knowledge" if load_environment else "telecom_demo_knowledge"
        if type(load_environment) is not bool or database.name != expected:
            raise ValueError("Unexpected knowledge database")
        self.db: Database[dict[str, Any]] = database.with_options(
            codec_options=CodecOptions(tz_aware=True)
        )

    def owner_active(self, tenant: str, owner: str) -> bool:
        return (
            self.db.owners.find_one({"tenant_id": tenant, "owner_id": owner, "active": True})
            is not None
        )

    def owner_can_publish(self, tenant: str, owner: str, actor: str) -> bool:
        return (
            self.db.owners.find_one(
                {"tenant_id": tenant, "owner_id": owner, "active": True, "user_ids": actor}
            )
            is not None
        )

    def approval_valid(self, version: Version, digest: str) -> bool:
        return (
            self.db.review_events.find_one(
                {
                    "tenant_id": version.tenant_id,
                    "version_key": version_key(version),
                    "metadata_digest": digest,
                    "actor": version.approved_by,
                }
            )
            is not None
        )

    def source_verified(self, version: Version) -> bool:
        return (
            self.db.review_events.find_one(
                {
                    "tenant_id": version.tenant_id,
                    "version_key": version_key(version),
                    "source_checksum": version.checksum,
                    "metadata_digest": version.approval_digest(),
                }
            )
            is not None
        )

    def current_version(self, tenant: str, document: str) -> tuple[str, int] | None:
        row = self.db.documents.find_one(
            {"_id": document_key(tenant, document), "tenant_id": tenant}
        )
        return (row["version_id"], row["revision"]) if row else None

    def conflict_confirmed(self, tenant: str, document: str) -> bool:
        row = self.db.documents.find_one(
            {"_id": document_key(tenant, document), "tenant_id": tenant}
        )
        return bool(row and row.get("conflict", True))


