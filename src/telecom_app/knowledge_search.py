"""Bounded native hybrid query and authoritative, extractive citation release."""

import hashlib
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .knowledge import Authority, Scope, Version, assess, utc_now

DIMENSIONS = 1024
PROFILE = "voyage-context-4:1024:v1"
LEXICAL_INDEX = "knowledge_lexical_v1"
VECTOR_INDEX = "knowledge_context_1024_v1"
FILTER_FIELDS = ("tenant_id", "acl", "product", "region", "firmware_range", "language",
                 "status", "embedding_profile", "eligible", "effective_from", "expires_at",
                 "review_due_at")


def index_definitions() -> list[dict[str, Any]]:
    fields: dict[str, Any] = {key: {"type": "token"} for key in FILTER_FIELDS}
    fields.update({key: {"type": "date"} for key in
                   ("effective_from", "expires_at", "review_due_at")})
    fields.update(text={"type": "string"}, eligible={"type": "boolean"})
    return [
        {"name": LEXICAL_INDEX, "type": "search", "definition": {
            "analyzer": "lucene.standard", "mappings": {"dynamic": False, "fields": fields}}},
        {"name": VECTOR_INDEX, "type": "vectorSearch", "definition": {"fields": [
            {"type": "vector", "path": "embedding", "numDimensions": DIMENSIONS,
             "similarity": "cosine"},
            *[{"type": "filter", "path": key} for key in FILTER_FIELDS]]}},
    ]


def hybrid_pipeline(scope: Scope, query: str, vector: Sequence[float],
                    now: datetime) -> list[dict[str, Any]]:
    import math

    if scope.language not in ("en", "pt", "es"):
        raise ValueError("Unsupported source language")
    if not query.strip() or len(query) > 2000 or not scope.readers or now.tzinfo is None:
        raise ValueError("Bounded query and authenticated scope required")
    if len(vector) != DIMENSIONS or any(not math.isfinite(v) for v in vector):
        raise ValueError("Wrong embedding profile")
    equals = {"tenant_id": scope.tenant_id, "product": scope.product, "region": scope.region,
              "firmware_range": scope.firmware_range, "language": scope.language,
              "status": "published", "embedding_profile": PROFILE, "eligible": True}
    filters: list[dict[str, Any]] = [
        *[{key: {"$eq": value}} for key, value in equals.items()],
        {"acl": {"$in": sorted(scope.readers)}},
        {"effective_from": {"$lte": now}}, {"expires_at": {"$gt": now}},
        {"review_due_at": {"$gt": now}},
    ]
    lexical = [*[{"equals": {"path": key, "value": value}} for key, value in equals.items()],
               {"in": {"path": "acl", "value": sorted(scope.readers)}},
               {"range": {"path": "effective_from", "lte": now}},
               {"range": {"path": "expires_at", "gt": now}},
               {"range": {"path": "review_due_at", "gt": now}}]
    return [{"$rankFusion": {"input": {"pipelines": {
        "lexical": [{"$search": {"index": LEXICAL_INDEX, "compound": {
            "must": [{"text": {"path": "text", "query": query}}], "filter": lexical}}},
                    {"$limit": 20}],
        "semantic": [{"$vectorSearch": {"index": VECTOR_INDEX, "path": "embedding",
            "queryVector": list(vector), "numCandidates": 400, "limit": 20,
            "filter": {"$and": filters}}}],
    }}, "combination": {"weights": {"lexical": 0.5, "semantic": 0.5}}}}, {"$limit": 20},
        {"$project": {"_id": 0, "chunk_id": 1, "version_key": 1, "revision": 1,
                      "text": 1, "text_sha256": 1, "pages": 1}}]


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    chunk_id: str = Field(min_length=1, max_length=128)
    version_key: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=1, strict=True)
    text: str = Field(min_length=1, max_length=8000)
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pages: tuple[int, ...] = Field(max_length=10)


class KnowledgeReader(Protocol):
    def search(self, pipeline: list[dict[str, Any]]) -> list[Candidate]: ...
    def version(self, tenant: str, key: str) -> Version | None: ...
    def chunk(self, tenant: str, version_key: str, key: str, revision: int) -> Candidate | None: ...


class Reranker(Protocol):
    def rank(self, query: str, texts: list[str]) -> list[int]: ...


class CandidateCache(Protocol):
    def lookup(self, scope: Scope, query: str, vector: Sequence[float],
               now: datetime) -> list[Candidate] | None: ...
    def store(self, scope: Scope, query: str, vector: Sequence[float],
              candidates: list[Candidate], now: datetime) -> None: ...



_MESSAGES = {
    "empty": {
        "en": "No currently approved procedure matches your access and equipment. Contact support.",
        "pt": ("Nenhum procedimento aprovado em português corresponde ao seu acesso e equipamento. "
               "Contate o suporte."),
        "es": ("Ningún procedimiento aprobado en español corresponde a tu acceso y equipo. "
               "Contacta con soporte."),
    },
    "oversize": {
        "en": "The approved procedure exceeds the response limit. Contact support.",
        "pt": "O procedimento aprovado excede o limite da resposta. Contate o suporte.",
        "es": "El procedimiento aprobado supera el límite de respuesta. Contacta con soporte.",
    },
    "changed": {
        "en": "The procedure changed before release. Contact support for current guidance.",
        "pt": ("O procedimento mudou antes da resposta. "
               "Contate o suporte para obter orientação atual."),
        "es": ("El procedimiento cambió antes de la respuesta. "
               "Contacta con soporte para obtener ayuda actual."),
    },
}


def knowledge_message(kind: str, language: str) -> str:
    if language not in ("en", "pt", "es"):
        raise ValueError("Unsupported source language")
    return _MESSAGES[kind][language]

def retrieve(reader: KnowledgeReader, authority: Authority, reranker: Reranker,
             scope: Scope, query: str, vector: Sequence[float],
             clock: Callable[[], datetime] = utc_now, *, max_response_chars: int = 7500,
             cache: CandidateCache | None = None) -> str:
    if type(max_response_chars) is not int or not 256 <= max_response_chars <= 7500:
        raise ValueError("Invalid citation response budget")
    pipeline = hybrid_pipeline(scope, query, vector, clock())
    cached = None
    if cache is not None:
        try:
            cached = cache.lookup(scope, query, vector, clock())
        except Exception:
            # Optional optimization failure must retain the governed retrieval path.
            cached = None
    if cached and (len(cached) > 20 or len({(c.version_key, c.chunk_id, c.revision)
                                          for c in cached}) != len(cached)):
        cached = None
    candidates = cached if cached else reader.search(pipeline)
    if len(candidates) > 20 or len({(c.version_key, c.chunk_id, c.revision)
                                   for c in candidates}) != len(candidates):
        raise ValueError("Unbounded or duplicate search result")

    def verified(candidate: Candidate) -> Version | None:
        # Re-read source text too: an index payload cannot forge an eligible citation.
        original = reader.chunk(scope.tenant_id, candidate.version_key,
                                candidate.chunk_id, candidate.revision)
        version = reader.version(scope.tenant_id, candidate.version_key)
        if (original != candidate or version is None or candidate.revision != version.revision
                or hashlib.sha256(candidate.text.encode()).hexdigest() != candidate.text_sha256
                or any(type(page) is not int or not 1 <= page <= 10 for page in candidate.pages)
                or not assess(version, scope, clock(), authority).eligible):
            return None
        return version

    valid = [candidate for candidate in candidates if verified(candidate)]
    if cached and len(valid) != len(candidates):
        # Any stale cached source discards the entire set and refreshes from search.
        candidates = reader.search(pipeline)
        if len(candidates) > 20 or len({(c.version_key, c.chunk_id, c.revision)
                                       for c in candidates}) != len(candidates):
            raise ValueError("Unbounded or duplicate search result")
        valid = [candidate for candidate in candidates if verified(candidate)]
        cached = None
    if not cached and cache is not None and valid:
        try:
            cache.store(scope, query, vector, valid, clock())
        except Exception:
            pass  # A cache write never authorizes or prevents authoritative release.
    if not valid:
        return knowledge_message("empty", scope.language)
    order = reranker.rank(query, [candidate.text for candidate in valid])
    if (len(order) > 3 or len(set(order)) != len(order)
            or any(type(i) is not int or not 0 <= i < len(valid) for i in order)):
        raise ValueError("Invalid reranker result")
    result: list[str] = []
    for index in order:
        candidate = valid[index]
        version = verified(candidate)
        if version is None:
            continue
        labels = {"en": ("version", "pages", "unknown"),
                  "pt": ("versão", "páginas", "desconhecidas"),
                  "es": ("versión", "páginas", "desconocidas")}[scope.language]
        pages = ", ".join(map(str, candidate.pages)) if candidate.pages else labels[2]
        excerpt = (f"{candidate.text}\n[{version.document_id}, {labels[0]} {version.version_id}, "
                   f"{labels[1]} {pages}]")
        # Never truncate a procedure: an omitted final step can change its meaning.
        # Leave headroom within the existing 8,000-character journey/voice contract.
        if len("\n\n".join([*result, excerpt])) > max_response_chars:
            return knowledge_message("oversize", scope.language)
        result.append(excerpt)
    # No second model gets to rewrite operational instructions or invent citations.
    return "\n\n".join(result) if result else knowledge_message("changed", scope.language)
