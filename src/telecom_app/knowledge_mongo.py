"""Read-only MongoDB knowledge adapter; native approval authority is injected separately."""

from typing import Any

from bson.codec_options import CodecOptions
from pymongo.database import Database

from .knowledge import Version
from .knowledge_search import Candidate


class MongoKnowledgeReader:
    def __init__(self, database: Database[dict[str, Any]], *,
                 load_environment: bool = False) -> None:
        # Trusted process construction only; HTTP callers cannot select a namespace.
        expected = "telecom_load_knowledge" if load_environment else "telecom_demo_knowledge"
        if type(load_environment) is not bool or database.name != expected:
            raise ValueError("Unexpected knowledge database")
        # Reuse the caller's client/pool. BSON UTC dates must remain timezone-aware.
        self.database: Database[dict[str, Any]] = database.with_options(
            codec_options=CodecOptions(tz_aware=True))

    def search(self, pipeline: list[dict[str, Any]]) -> list[Candidate]:
        # Only the backend-generated pipeline is accepted by the application contract.
        # Read at most 21 to detect an over-budget result without an unbounded list.
        with self.database.chunks.aggregate(pipeline, maxTimeMS=15000) as cursor:
            rows: list[Candidate] = []
            for row in cursor:
                if len(rows) == 20:
                    raise ValueError("Search result exceeded the candidate budget")
                rows.append(Candidate.model_validate(row))
        return rows

    def version(self, tenant: str, key: str) -> Version | None:
        row = self.database.document_versions.find_one(
            {"tenant_id": tenant, "_id": key}, {"_id": 0}, max_time_ms=15000)
        return Version.model_validate(row) if row is not None else None

    def chunk(self, tenant: str, version_key: str, key: str, revision: int) -> Candidate | None:
        row = self.database.chunks.find_one(
            {"tenant_id": tenant, "version_key": version_key,
             "chunk_id": key, "revision": revision},
            {"_id": 0, **dict.fromkeys(Candidate.model_fields, 1)}, max_time_ms=15000)
        return Candidate.model_validate(row) if row is not None else None
