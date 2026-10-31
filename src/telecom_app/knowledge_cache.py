"""Optional bounded candidate cache; authoritative source release remains in retrieval."""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from bson.codec_options import CodecOptions
from pymongo.collection import Collection
from pymongo.database import Database

from .knowledge import POLICY, Scope
from .knowledge_search import PROFILE, Candidate, KnowledgeReader

INDEX = "retrieval_cache_context_1024_v1"
MAX_ENTRIES = 128
MAX_AGE = timedelta(minutes=15)
# Calibrated for the bounded synthetic demo; see Phase 5 evidence, not a general guarantee.
SIMILARITY = .91


def scope_key(scope: Scope) -> str:
    return hashlib.sha256(json.dumps([
        scope.tenant_id, sorted(scope.readers), scope.product, scope.region,
        scope.firmware_range, scope.language, POLICY, PROFILE,
    ], separators=(",", ":")).encode()).hexdigest()


class MongoCandidateCache:
    def __init__(self, database: Database[dict[str, Any]], reader: KnowledgeReader, *,
                 load_environment: bool = False) -> None:
        # Trusted process construction only; HTTP callers cannot select a namespace.
        expected = "telecom_load_knowledge" if load_environment else "telecom_demo_knowledge"
        if type(load_environment) is not bool or database.name != expected:
            raise ValueError("Unexpected cache database")
        self.collection: Collection[dict[str, Any]] = database.with_options(
            codec_options=CodecOptions(tz_aware=True)).retrieval_cache
        self.reader = reader

    def lookup(self, scope: Scope, query: str, vector: Sequence[float],
               now: datetime) -> list[Candidate] | None:
        filters = {"tenant_id": scope.tenant_id, "scope_key": scope_key(scope),
                   "policy_version": POLICY, "embedding_profile": PROFILE,
                   "expires_at": {"$gt": now}}
        matches = list(self.collection.aggregate([
            {"$vectorSearch": {"index": INDEX, "path": "embedding", "queryVector": list(vector),
                               "filter": filters, "exact": True, "limit": 1}},
            {"$project": {"embedding": 0}},
            {"$set": {"score": {"$meta": "vectorSearchScore"}}},
        ]))
        if not matches:
            return None
        indexed = matches[0]
        # Search index freshness cannot authorize use of an expired/overwritten slot.
        row = self.collection.find_one({"_id": indexed["_id"], **filters})
        if (row is None or row.get("query_sha256") != indexed.get("query_sha256")
                or row.get("created_at") != indexed.get("created_at")
                or row.get("sources") != indexed.get("sources")
                or not isinstance(indexed.get("score"), (int, float))
                or not indexed["score"] >= SIMILARITY
                or not now - MAX_AGE <= row["created_at"] <= now
                or not now < row["expires_at"] <= row["created_at"] + MAX_AGE):
            return None
        references = row.get("sources")
        if not isinstance(references, list) or not 1 <= len(references) <= 20:
            return None
        candidates = []
        for ref in references:
            candidate = self.reader.chunk(scope.tenant_id, ref["version_key"],
                                          ref["chunk_id"], ref["revision"])
            if candidate is None or candidate.text_sha256 != ref["text_sha256"]:
                return None
            candidates.append(candidate)
        return candidates

    def store(self, scope: Scope, query: str, vector: Sequence[float],
              candidates: list[Candidate], now: datetime) -> None:
        if not 1 <= len(candidates) <= 20:
            return
        expiry = now + MAX_AGE
        for candidate in candidates:
            version = self.reader.version(scope.tenant_id, candidate.version_key)
            if version is None:
                return
            expiry = min(expiry, version.expires_at, version.review_due_at)
        if expiry <= now:
            return
        scope_hash = scope_key(scope)
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        identity = hashlib.sha256((scope_hash + query_hash).encode()).hexdigest()
        # Fixed slots bound global storage even with concurrent writers or delayed TTL.
        # A collision only evicts a candidate set; scope is rechecked on every read.
        slot = "cache-slot-" + str(int(identity, 16) % MAX_ENTRIES)
        self.collection.replace_one({"_id": slot}, {
            "_id": slot, "tenant_id": scope.tenant_id, "scope_key": scope_hash,
            "policy_version": POLICY, "embedding_profile": PROFILE,
            "query_sha256": query_hash, "embedding": list(vector),
            "created_at": now, "expires_at": expiry,
            "sources": [{k: getattr(candidate, k) for k in
                         ("version_key", "chunk_id", "revision", "text_sha256")}
                        for candidate in candidates],
        }, upsert=True)
