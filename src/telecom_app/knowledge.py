"""Knowledge-domain contracts; search relevance never grants publication or access."""

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

POLICY = "demo-v1"
MAX_PAGES = 10
MAX_TEXT = 60_000
MAX_CHUNKS = 32


class Version(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenant_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    version_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=200)
    information_owner: str = Field(min_length=1, max_length=128)
    created_at: AwareDatetime
    ingested_at: AwareDatetime
    effective_from: AwareDatetime
    expires_at: AwareDatetime
    last_reviewed_at: AwareDatetime
    review_due_at: AwareDatetime
    reviewed_by: str = Field(min_length=1, max_length=128)
    approved_by: str = Field(min_length=1, max_length=128)
    approved_at: AwareDatetime
    source_uri: str = Field(min_length=1, max_length=512)
    source_system: str = Field(min_length=1, max_length=128)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    classification: Literal["internal-demo"]
    acl: tuple[str, ...] = Field(min_length=1, max_length=16)
    language: Literal["en"]
    product: str = Field(min_length=1, max_length=128)
    region: str = Field(min_length=1, max_length=128)
    firmware_range: str = Field(min_length=1, max_length=64)
    supersedes: str | None = None
    superseded_by: str | None = None
    status: Literal["draft", "in_review", "approved", "published", "quarantined", "expired",
                    "superseded", "revoked"]
    business_impact: Literal["low", "high"]
    change_rate: Literal["low", "high"]

    @field_validator("created_at", "ingested_at", "effective_from", "expires_at",
                     "last_reviewed_at", "review_due_at", "approved_at")
    @classmethod
    def bson_precision(cls, value: datetime) -> datetime:
        # MongoDB stores milliseconds. Canonicalize before hashing reviewed metadata
        # so an unchanged version retains its digest after a BSON round trip.
        return value.astimezone(UTC).replace(microsecond=value.microsecond // 1000 * 1000)

    @model_validator(mode="after")
    def chronology(self) -> Version:
        if not (self.created_at <= self.effective_from < self.expires_at
                and self.created_at <= self.last_reviewed_at < self.review_due_at
                and self.created_at <= self.approved_at
                and self.created_at <= self.ingested_at):
            raise ValueError("Invalid source chronology")
        if any(not value.strip() or len(value) > 128 for value in self.acl):
            raise ValueError("Invalid reader scope")
        return self

    def approval_digest(self) -> str:
        # Status and ingestion time are server lifecycle fields, not source validity.
        value = self.model_dump(mode="json", exclude={"status", "ingested_at", "superseded_by"})
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Scope:
    """Construct from authenticated server-side entitlements, never model arguments."""

    tenant_id: str
    readers: frozenset[str]
    product: str
    region: str
    firmware_range: str
    language: str = "en"


class Authority(Protocol):
    def owner_active(self, tenant: str, owner: str) -> bool: ...
    def approval_valid(self, version: Version, digest: str) -> bool: ...
    def source_verified(self, version: Version) -> bool: ...
    def current_version(self, tenant: str, document: str) -> tuple[str, int] | None: ...
    def conflict_confirmed(self, tenant: str, document: str) -> bool: ...


@dataclass(frozen=True)
class Assessment:
    score: int
    band: str
    factors: Mapping[str, int]
    blockers: tuple[str, ...]
    as_of: datetime
    policy: str = POLICY

    @property
    def eligible(self) -> bool:
        return not self.blockers


def utc_now() -> datetime:
    return datetime.now(UTC)


def assess(version: Version, scope: Scope, now: datetime, authority: Authority,
           *, publication: bool = False) -> Assessment:
    if now.tzinfo is None:
        raise ValueError("An aware UTC instant is required")
    owner = authority.owner_active(version.tenant_id, version.information_owner)
    verified = authority.source_verified(version) and authority.approval_valid(
        version, version.approval_digest())
    active = authority.current_version(version.tenant_id, version.document_id)
    replaced = bool(version.superseded_by) or authority.conflict_confirmed(
        version.tenant_id, version.document_id)
    if not publication and active != (version.version_id, version.revision):
        replaced = True
    factors = {name: weight for name, condition, weight in (
        ("expired", now >= version.expires_at, 30),
        ("review_overdue", now >= version.review_due_at, 15),
        ("replacement_or_conflict", replaced, 25),
        ("owner_unresolved", not owner, 10),
        ("unverified", not verified, 10),
        ("high_impact", version.business_impact == "high", 5),
        ("rapid_change", version.change_rate == "high", 5),
    ) if condition}
    blockers = [name for name in factors if name not in ("high_impact", "rapid_change")]
    if version.status not in (("approved",) if publication else ("published",)):
        blockers.append("not_approved" if publication else "not_published")
    if now < version.effective_from:
        blockers.append("not_effective")
    if version.approved_at > now or version.last_reviewed_at > now:
        blockers.append("future_review_or_approval")
    if version.tenant_id != scope.tenant_id or not scope.readers.intersection(version.acl):
        blockers.append("access_denied")
    if (version.product, version.region, version.firmware_range, version.language) != (
            scope.product, scope.region, scope.firmware_range, scope.language):
        blockers.append("not_applicable")
    score = min(100, sum(factors.values()))
    band = ("low" if score < 20 else "moderate" if score < 40
            else "high" if score < 70 else "critical")
    if score >= 40:
        blockers.append("quarantined_risk")
    return Assessment(score, band, factors, tuple(blockers), now)


def canonical(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


@dataclass(frozen=True)
class AlignedChunk:
    text: str
    pages: tuple[int, ...]
    page_known: bool
    text_sha256: str


def align_chunks(pages: Sequence[str], chunks: Sequence[str]) -> list[AlignedChunk]:
    """Exact normalized provenance; repeated or rewritten text gets no invented page."""
    if not 1 <= len(pages) <= MAX_PAGES or not 1 <= len(chunks) <= MAX_CHUNKS:
        raise ValueError("Document exceeds the bounded demo")
    normalized = [canonical(page) for page in pages]
    if not all(normalized) or sum(map(len, normalized)) > MAX_TEXT:
        raise ValueError("Empty page or oversized canonical document")
    full = " ".join(normalized)
    spans = []
    offset = 0
    for page in normalized:
        spans.append((offset, offset + len(page)))
        offset += len(page) + 1
    aligned = []
    for chunk in chunks:
        text = canonical(chunk)
        if not text or len(text) > 8000:
            raise ValueError("Empty or oversized chunk")
        start = full.find(text)
        unique = start >= 0 and full.find(text, start + 1) < 0
        found = tuple(i + 1 for i, (left, right) in enumerate(spans)
                      if unique and left < start + len(text) and right > start)
        aligned.append(AlignedChunk(text, found, bool(found),
                                    hashlib.sha256(text.encode()).hexdigest()))
    return aligned


def submission_key(tenant: str, document: str, version: str, checksum: str,
                   metadata_digest: str) -> str:
    """Exact resubmissions share an ID; changed source/metadata cannot reuse approval."""
    if not all((tenant, document, version, checksum, metadata_digest)):
        raise ValueError("Incomplete submission identity")
    return hashlib.sha256(json.dumps([tenant, document, version, checksum,
                                    metadata_digest], separators=(",", ":")).encode()).hexdigest()
