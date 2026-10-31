"""Durable bounded PDF staging. This domain never writes published knowledge."""

import hashlib
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from bson.codec_options import CodecOptions
from pymongo import ReturnDocument
from pymongo.client_session import ClientSession
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .ingestion_worker import validate_staged
from .knowledge import submission_key, utc_now

MAX_PDF_BYTES = 5_000_000
MAX_ACTIVE = 4
MAX_ATTEMPTS = 2
LEASE_SECONDS = 360


class IngestionConflict(RuntimeError):
    pass


class MongoIngestion:
    """Only an authorized curator adapter may submit; tenant is server-derived.

    One quota record serializes concurrent admission per tenant. Transaction
    callbacks contain database operations only, never provider calls or OCR.
    """

    def __init__(self, database: Database[dict[str, Any]],
                 clock: Callable[[], datetime] = utc_now, *,
                 load_environment: bool = False) -> None:
        # Trusted process construction only; HTTP callers cannot select a namespace.
        expected = "telecom_load_ingestion" if load_environment else "telecom_demo_ingestion"
        if type(load_environment) is not bool or database.name != expected:
            raise ValueError("Unexpected ingestion database")
        self.db: Database[dict[str, Any]] = database.with_options(
            codec_options=CodecOptions(tz_aware=True))
        self.clock = clock

    def submit(self, tenant: str, document: str, version: str, metadata_digest: str,
               pdf: bytes, *, scanned: bool = False,
               metadata: dict[str, Any] | None = None) -> str:
        if (not all(isinstance(value, str) and 1 <= len(value) <= 128
                    for value in (tenant, document, version))
                or len(metadata_digest) != 64
                or any(c not in "0123456789abcdef" for c in metadata_digest)
                or not 1 <= len(pdf) <= MAX_PDF_BYTES or not pdf.startswith(b"%PDF-")
                or type(scanned) is not bool):
            raise ValueError("Invalid bounded PDF submission")
        checksum = hashlib.sha256(pdf).hexdigest()
        # Processing mode is part of identity; switching OCR must not reuse a result.
        profile_digest = hashlib.sha256((metadata_digest + str(scanned)).encode()).hexdigest()
        key = submission_key(tenant, document, version, checksum, profile_digest)
        now = self.clock()

        def save(session: ClientSession) -> None:
            if self.db.jobs.find_one({"_id": key, "tenant_id": tenant}, session=session):
                return
            quota = "quota:" + tenant
            self.db.staged_artifacts.update_one(
                {"_id": quota}, {"$setOnInsert": {"tenant_id": tenant, "kind": "quota",
                                                "active": 0}}, upsert=True, session=session)
            admitted = self.db.staged_artifacts.update_one(
                {"_id": quota, "tenant_id": tenant, "active": {"$lt": MAX_ACTIVE}},
                {"$inc": {"active": 1}}, session=session)
            if admitted.modified_count != 1:
                raise IngestionConflict("The tenant ingestion queue is full")
            self.db.staged_artifacts.insert_one({
                "_id": key, "kind": "pdf", "tenant_id": tenant, "pdf": pdf,
                "checksum": checksum, "created_at": now}, session=session)
            self.db.jobs.insert_one({
                "_id": key, "tenant_id": tenant, "submission_key": key,
                "document_id": document, "version_id": version,
                "metadata_digest": metadata_digest, "checksum": checksum, "scanned": scanned,
                "status": "queued", "attempts": 0, "available_at": now, "created_at": now,
                "lease_token": None, "lease_until": now, "failure": None,
                "metadata": metadata,
            }, session=session)

        # Concurrent first admissions can race while inserting the quota record.
        # Retry only this database-only transaction, never external work.
        for attempt in range(3):
            try:
                with self.db.client.start_session() as session:
                    session.with_transaction(save)
                break
            except DuplicateKeyError:
                if attempt == 2:
                    raise IngestionConflict(
                        "Concurrent submission; retry the same request") from None
        return key

    def claim(self, tenant: str, job_id: str | None = None) -> dict[str, Any] | None:
        now = self.clock()
        return self.db.jobs.find_one_and_update(
            {"tenant_id": tenant, **({"_id": job_id} if job_id is not None else {}),
             "attempts": {"$lt": MAX_ATTEMPTS}, "$or": [
                {"status": "queued", "available_at": {"$lte": now}},
                {"status": "running", "lease_until": {"$lte": now}},
            ]}, {"$set": {"status": "running", "lease_token": uuid4().hex,
                         "lease_until": now + timedelta(seconds=LEASE_SECONDS)},
                 "$inc": {"attempts": 1}}, sort=[("available_at", 1), ("_id", 1)],
            return_document=ReturnDocument.AFTER)

    def source(self, job: dict[str, Any]) -> bytes:
        row = self.db.staged_artifacts.find_one({"_id": job["_id"],
                                               "tenant_id": job["tenant_id"], "kind": "pdf"})
        if row is None:
            raise IngestionConflict("Original PDF is unavailable")
        pdf = bytes(row["pdf"])
        if hashlib.sha256(pdf).hexdigest() != job["checksum"]:
            raise IngestionConflict("Original PDF integrity failed")
        return pdf

    def finish(self, job: dict[str, Any], result: dict[str, Any] | None,
               *, failure: str | None = None) -> None:
        if (result is None) == (failure is None):
            raise ValueError("Expected exactly one staging result or failure")
        if failure not in (None, "invalid_document", "provider_failure", "worker_failure"):
            raise ValueError("Use a sanitized failure category")
        if result is not None:
            validate_staged(result, job["checksum"], job["scanned"])
        def commit(session: ClientSession) -> None:
            now = self.clock()
            changed = self.db.jobs.update_one({
                "_id": job["_id"], "tenant_id": job["tenant_id"], "status": "running",
                "lease_token": job["lease_token"], "lease_until": {"$gt": now}},
                {"$set": {"status": "failed" if failure else "staged", "failure": failure,
                          "finished_at": now}}, session=session)
            if changed.modified_count != 1:
                raise IngestionConflict("Worker lease expired or was superseded")
            if result is not None:
                changed = self.db.staged_artifacts.update_one(
                    {"_id": job["_id"], "tenant_id": job["tenant_id"], "kind": "pdf"},
                    {"$set": {"result": result}}, session=session)
                if changed.matched_count != 1:
                    raise IngestionConflict("Original PDF is unavailable")
            self.db.staged_artifacts.update_one(
                {"_id": "quota:" + job["tenant_id"], "tenant_id": job["tenant_id"]},
                {"$inc": {"active": -1}}, session=session)

        with self.db.client.start_session() as session:
            session.with_transaction(commit)

    def expire_exhausted(self, tenant: str) -> int:
        """Release quota after the final crashed attempt, without another paid call."""
        now = self.clock()

        def expire(session: ClientSession) -> int:
            result = self.db.jobs.update_many(
                {"tenant_id": tenant, "status": "running", "attempts": MAX_ATTEMPTS,
                 "lease_until": {"$lte": now}},
                {"$set": {"status": "failed", "failure": "worker_failure", "finished_at": now}},
                session=session)
            if result.modified_count:
                self.db.staged_artifacts.update_one(
                    {"_id": "quota:" + tenant, "tenant_id": tenant},
                    {"$inc": {"active": -result.modified_count}}, session=session)
            return result.modified_count

        with self.db.client.start_session() as session:
            return session.with_transaction(expire)
