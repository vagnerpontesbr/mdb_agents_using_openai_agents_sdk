"""Atomic domain publication after verified native Engine approval."""

import hashlib
import time
from datetime import datetime
from typing import Any

from pymongo.client_session import ClientSession

from .document_review import NativePublicationApproval, request_data, request_digest
from .ingestion_worker import validate_staged
from .knowledge import Scope, Version, assess, utc_now
from .knowledge_authority import MongoKnowledgeAuthority, document_key, version_key
from .knowledge_search import PROFILE


class PublicationConflict(RuntimeError):
    pass


class MongoKnowledgePublisher(MongoKnowledgeAuthority):
    def publish(
        self,
        *,
        job: dict[str, Any],
        version: Version,
        pdf: bytes,
        staged: dict[str, Any],
        approval: NativePublicationApproval,
    ) -> str:
        if (
            job["status"] != "staged"
            or job["tenant_id"] != version.tenant_id
            or job["document_id"] != version.document_id
            or job["version_id"] != version.version_id
            or job["metadata_digest"] != version.approval_digest()
            or hashlib.sha256(pdf).hexdigest() != version.checksum
            or approval.request_digest != request_digest(request_data(job["_id"], version))
            or approval.requester != version.approved_by
        ):
            raise PublicationConflict("Source or native approval does not match the exact version")
        validate_staged(staged, version.checksum, job["scanned"])
        key, pointer = version_key(version), document_key(version.tenant_id, version.document_id)
        receipt_id = hashlib.sha256(
            (approval.execution_id + approval.request_digest).encode()
        ).hexdigest()

        def publish_transaction(session: ClientSession) -> str:
            if not time.time() < approval.expires_at:
                raise PublicationConflict("Native publication approval expired")
            owner = self.db.owners.find_one(
                {
                    "tenant_id": version.tenant_id,
                    "owner_id": version.information_owner,
                    "active": True,
                    "user_ids": approval.requester,
                },
                session=session,
            )
            if owner is None:
                raise PublicationConflict("Current owner permission is required")
            prior = self.db.review_events.find_one(
                {"_id": receipt_id, "tenant_id": version.tenant_id}, session=session
            )
            if prior:
                if (
                    prior["version_key"] != key
                    or prior["metadata_digest"] != version.approval_digest()
                ):
                    raise PublicationConflict("Publication receipt mismatch")
                return key
            current = self.db.documents.find_one(
                {"_id": pointer, "tenant_id": version.tenant_id}, session=session
            )
            if (
                current
                and (current.get("conflict", True) or version.supersedes != current["version_key"])
                or not current
                and version.supersedes is not None
            ):
                raise PublicationConflict("Replacement must bind the exact current version")
            now = utc_now()

            publisher = self
            # The transaction has just verified native approval, original bytes and owner.
            # Eligibility still uses the same canonical domain assessment.
            class PublicationAuthority:
                def owner_active(self, tenant: str, owner: str) -> bool:
                    return True

                def approval_valid(self, candidate: Version, digest: str) -> bool:
                    return digest == version.approval_digest()

                def source_verified(self, candidate: Version) -> bool:
                    return candidate.checksum == version.checksum

                def current_version(self, tenant: str, document: str) -> tuple[str, int] | None:
                    return None

                def conflict_confirmed(self, tenant: str, document: str) -> bool:
                    return False

                def translation_valid(self, candidate: Version, scope: Scope,
                                      now: datetime) -> bool:
                    return publisher.translation_valid(candidate, scope, now)

            approved = version.model_copy(update={"status": "approved"})
            scope = Scope(
                version.tenant_id,
                frozenset(version.acl),
                version.product,
                version.region,
                version.firmware_range,
                version.language,
            )
            if not assess(approved, scope, now, PublicationAuthority(), publication=True).eligible:
                raise PublicationConflict("Document is not currently eligible for publication")
            if self.db.document_versions.find_one({"_id": key}, session=session):
                raise PublicationConflict("Immutable version already exists")
            published = version.model_copy(
                update={"status": "published", "ingested_at": job["created_at"]}
            )
            self.db.document_versions.insert_one(
                {"_id": key, **published.model_dump()}, session=session
            )
            for index, chunk in enumerate(staged["chunks"]):
                self.db.chunks.insert_one(
                    {
                        "_id": key + ":" + str(index),
                        "version_key": key,
                        "chunk_id": str(index),
                        "revision": version.revision,
                        **chunk,
                        **{
                            name: getattr(published, name)
                            for name in (
                                "tenant_id",
                                "acl",
                                "product",
                                "region",
                                "firmware_range",
                                "language",
                                "status",
                                "effective_from",
                                "expires_at",
                                "review_due_at",
                            )
                        },
                        "eligible": True,
                        "embedding_profile": PROFILE,
                    },
                    session=session,
                )
            if current:
                self.db.document_versions.update_one(
                    {"_id": current["version_key"], "tenant_id": version.tenant_id},
                    {"$set": {"status": "superseded", "superseded_by": key}},
                    session=session,
                )
                self.db.chunks.update_many(
                    {"version_key": current["version_key"], "tenant_id": version.tenant_id},
                    {"$set": {"status": "superseded", "eligible": False}},
                    session=session,
                )
            self.db.documents.replace_one(
                {"_id": pointer},
                {
                    "_id": pointer,
                    "tenant_id": version.tenant_id,
                    "document_id": version.document_id,
                    "version_key": key,
                    "version_id": version.version_id,
                    "revision": version.revision,
                    "conflict": False,
                },
                upsert=True,
                session=session,
            )
            self.db.review_events.insert_one(
                {
                    "_id": receipt_id,
                    "tenant_id": version.tenant_id,
                    "execution_id": approval.execution_id,
                    "action_digest": approval.request_digest,
                    "version_key": key,
                    "metadata_digest": version.approval_digest(),
                    "actor": approval.requester,
                    "source_checksum": version.checksum,
                    "job_id": job["_id"],
                    "recorded_at": now,
                },
                session=session,
            )
            return key

        with self.db.client.start_session() as session:
            return session.with_transaction(publish_transaction)
