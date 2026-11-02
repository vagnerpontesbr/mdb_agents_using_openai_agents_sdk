"""Demo role/owner authorization and service-domain handoff for governed PDFs."""

import base64
import hashlib
import os
import subprocess
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from compatibility.demo_auth.auth import AccessDenied

from .document_review import DocumentReview
from .identity import IdentityService
from .ingestion import MongoIngestion
from .knowledge import Scope, Version, assess, utc_now
from .knowledge_cache import MongoCandidateCache
from .knowledge_mongo import MongoKnowledgeReader
from .knowledge_publication import MongoKnowledgePublisher, PublicationConflict
from .knowledge_search import CandidateCache, retrieve
from .knowledge_voyage import VoyageKnowledge
from .turn_locale import validated_locale

TENANT = "synthetic-telecom"
OWNER = "demo-document-owner"
SCOPE = Scope(TENANT, frozenset({"synthetic-support"}), "FiberBox", "demo", "2.x")


class Upload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pdf_base64: str = Field(min_length=1, max_length=6_666_668)
    document_id: str = Field(min_length=1, max_length=100)
    version_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    created_at: AwareDatetime
    effective_from: AwareDatetime
    expires_at: AwareDatetime
    review_due_at: AwareDatetime
    last_reviewed_at: AwareDatetime
    supersedes: str | None = Field(default=None, max_length=128)
    scanned: bool = False
    language: Literal["en", "pt", "es"] = "en"
    translation_of: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class CurationService:
    def __init__(
        self,
        identity: IdentityService,
        ingestion: MongoIngestion,
        publisher: MongoKnowledgePublisher,
        reader: MongoKnowledgeReader,
        review: DocumentReview,
        voyage: VoyageKnowledge,
        cache: CandidateCache | None = None,
    ) -> None:
        self.identity, self.ingestion, self.publisher = identity, ingestion, publisher
        self.reader, self.review, self.voyage = reader, review, voyage
        self.cache = cache
        self._worker: subprocess.Popen[bytes] | None = None
        self._worker_lock = threading.Lock()

    def admin(self, token: str) -> str:
        actor = self.identity.principal(token)
        if actor.role != "admin":
            raise AccessDenied("Administrator required")
        return str(actor.user_id)

    def owner(self, token: str, version: Version) -> str:
        actor = self.admin(token)
        if not self.publisher.owner_can_publish(TENANT, version.information_owner, actor):
            raise AccessDenied("Document owner required")
        return actor

    def upload(self, token: str, data: Upload) -> dict[str, str]:
        self.admin(token)
        pdf = base64.b64decode(data.pdf_base64, validate=True)
        now = utc_now()
        owner = self.publisher.db.owners.find_one(
            {"tenant_id": TENANT, "owner_id": OWNER, "active": True}
        )
        if owner is None or len(owner["user_ids"]) != 1:
            raise PublicationConflict("Initial document owner is unavailable")
        checksum = hashlib.sha256(pdf).hexdigest()
        version = Version(
            tenant_id=TENANT,
            document_id=data.document_id,
            version_id=data.version_id,
            revision=1,
            title=data.title,
            information_owner=OWNER,
            created_at=data.created_at,
            ingested_at=now,
            effective_from=data.effective_from,
            expires_at=data.expires_at,
            last_reviewed_at=data.last_reviewed_at,
            review_due_at=data.review_due_at,
            reviewed_by=owner["user_ids"][0],
            approved_by=owner["user_ids"][0],
            approved_at=data.last_reviewed_at,
            source_uri="sha256:" + checksum,
            source_system="demo-upload",
            checksum=checksum,
            classification="internal-demo",
            acl=("synthetic-support",),
            language=data.language,
            translation_of=data.translation_of,
            product=SCOPE.product,
            region=SCOPE.region,
            firmware_range=SCOPE.firmware_range,
            supersedes=data.supersedes,
            status="draft",
            business_impact="high",
            change_rate="low",
        )
        job = self.ingestion.submit(
            TENANT,
            version.document_id,
            version.version_id,
            version.approval_digest(),
            pdf,
            scanned=data.scanned,
            metadata=version.model_dump(mode="json"),
        )
        return {"job_id": job, "status": "queued"}

    def jobs(self, token: str) -> list[dict[str, Any]]:
        self.admin(token)
        return list(
            self.ingestion.db.jobs.find(
                {"tenant_id": TENANT},
                {
                    "_id": 1,
                    "document_id": 1,
                    "version_id": 1,
                    "status": 1,
                    "failure": 1,
                    "attempts": 1,
                    "metadata": 1,
                },
            )
            .sort("created_at", -1)
            .limit(50)
        )

    def job(self, token: str, job_id: str) -> tuple[dict[str, Any], Version]:
        self.admin(token)
        job = self.ingestion.db.jobs.find_one({"_id": job_id, "tenant_id": TENANT})
        if job is None or not job.get("metadata"):
            raise PublicationConflict("Curated job is unavailable")
        return job, Version.model_validate(job["metadata"])

    def start_review(self, token: str, job_id: str) -> dict[str, Any]:
        job, version = self.job(token, job_id)
        self.owner(token, version)
        if job["status"] != "staged":
            raise PublicationConflict("Only a staged PDF can be reviewed")
        return self.review.create(token, job_id, version)

    def decide(self, token: str, execution_id: str, digest: str, decision: str) -> dict[str, Any]:
        pending = self.review.present(token, execution_id)
        if pending["status"] != "suspended":
            raise PublicationConflict("Publication is not awaiting review")
        self.owner(token, Version.model_validate(pending["request"]["metadata"]))
        return self.review.decide(token, execution_id, digest, decision)

    def publish(self, token: str, execution_id: str) -> dict[str, str]:
        state = self.review.present(token, execution_id)
        if state["status"] != "completed":
            raise PublicationConflict("Native review is incomplete")
        job_id = state["result"]["request"]["job_id"]
        job, version = self.job(token, job_id)
        self.owner(token, version)
        approval = self.review.verified(token, execution_id, job_id, version)
        artifact = self.ingestion.db.staged_artifacts.find_one({"_id": job_id, "tenant_id": TENANT})
        if not artifact or "result" not in artifact:
            raise PublicationConflict("Staged PDF is unavailable")
        key = self.publisher.publish(
            job=job,
            version=version,
            pdf=self.ingestion.source(job),
            staged=artifact["result"],
            approval=approval,
        )
        return {"version_key": key, "status": "published"}

    def search(self, token: str, query: str, *, cache_max_age_seconds: int = 900) -> str:
        self.identity.principal(token)
        locale = validated_locale(self.identity.profile(token)["locale"])
        scope = replace(SCOPE, language={"en-US": "en", "pt-BR": "pt", "es-ES": "es"}[locale])
        cache = self.cache
        if isinstance(cache, MongoCandidateCache):
            cache = cache.bounded(cache_max_age_seconds)
        elif cache is not None and cache_max_age_seconds != 900:
            raise RuntimeError("Cache does not support bounded request settings")
        response = retrieve(
            self.reader, self.publisher, self.voyage, scope, query, self.voyage.embed_query(query),
            cache=cache,
        )
        self.identity.principal(token)
        return response

    def process_next(self, token: str) -> dict[str, str]:
        self.admin(token)
        with self._worker_lock:
            if self._worker is not None and self._worker.poll() is None:
                return {"status": "running"}
            environment = {
                key: os.environ[key]
                for key in (
                    "PATH",
                    "HOME",
                    "UV_CACHE_DIR",
                    "INGESTION_MONGODB_URI",
                    "VOYAGE_API_KEY",
                    "VOYAGE_BASE_URL",
                )
                if key in os.environ
            }
            root = Path(__file__).resolve().parents[2]
            self._worker = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "--frozen",
                    "python",
                    "scripts/run_ingestion_worker.py",
                    "--tenant",
                    TENANT,
                    "--allow-provider-calls",
                ],
                cwd=root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {"status": "started"}

    def preview(self, token: str, job_id: str) -> bytes:
        job, _ = self.job(token, job_id)
        return self.ingestion.source(job)

    def documents(self, token: str) -> list[dict[str, str]]:
        self.identity.principal(token)
        documents = []
        for row in self.publisher.db.documents.find({"tenant_id": TENANT}).limit(50):
            version = self.reader.version(TENANT, row["version_key"])
            if version and assess(version, replace(SCOPE, language=version.language),
                                  utc_now(), self.publisher).eligible:
                documents.append(
                    {
                        "version_key": row["version_key"],
                        "title": version.title,
                        "document_id": version.document_id,
                        "version_id": version.version_id,
                        "language": version.language,
                        "translation_of": version.translation_of or "",
                    }
                )
        return documents

    def source(self, token: str, key: str) -> bytes:
        self.identity.principal(token)
        version = self.reader.version(TENANT, key)
        if version is None or not assess(version, replace(SCOPE, language=version.language),
                                         utc_now(), self.publisher).eligible:
            raise AccessDenied("Document access denied")
        event = self.publisher.db.review_events.find_one(
            {"tenant_id": TENANT, "version_key": key, "metadata_digest": version.approval_digest()}
        )
        if event is None:
            raise PublicationConflict("Source provenance is unavailable")
        job = self.ingestion.db.jobs.find_one({"_id": event["job_id"], "tenant_id": TENANT})
        if job is None:
            raise PublicationConflict("Original source is unavailable")
        pdf = self.ingestion.source(job)
        self.identity.principal(token)
        current = self.reader.version(TENANT, key)
        if current != version or not assess(version, replace(SCOPE, language=version.language),
                                           utc_now(), self.publisher).eligible:
            raise AccessDenied("Document access denied")
        return pdf
