"""Bounded official Voyage HTTP transport for contextual knowledge, without retries."""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .knowledge import MAX_CHUNKS, MAX_PAGES, MAX_TEXT, AlignedChunk, align_chunks, canonical
from .knowledge_search import DIMENSIONS

BASES = frozenset({"https://api.voyageai.com/v1", "https://ai.mongodb.com/v1",
                   "https://us.ai.mongodb.com/v1", "https://eu.ai.mongodb.com/v1"})


class ProviderUnavailable(RuntimeError):
    """Never include upstream payloads, document text or credentials in errors."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def post(base: str, key: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if base not in BASES or path not in ("contextualizedembeddings", "rerank") or not key:
        raise ValueError("Expected an official Voyage endpoint and injected credential")
    request = Request(base + "/" + path, data=json.dumps(payload, allow_nan=False).encode(),
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"},
                      method="POST")
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ProviderUnavailable("Provider response exceeds the knowledge limit")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ProviderUnavailable("Invalid provider response")
        return data
    except HTTPError as error:
        error.close()
        raise ProviderUnavailable("Provider request failed; no retry was attempted") from None
    except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        raise ProviderUnavailable("Provider transport failed; details suppressed") from None


def rows(value: Any, count: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CHUNKS:
        raise ValueError("Invalid embedding result count")
    if not all(isinstance(row, dict) for row in value):
        raise ValueError("Invalid embedding result")
    indices = [row.get("index") for row in value]
    if (any(type(index) is not int for index in indices)
            or sorted(indices) != list(range(len(value)))
            or count is not None and len(value) != count):
        raise ValueError("Invalid embedding result indices")
    return sorted(value, key=lambda row: row["index"])


def vector(value: Any) -> list[float]:
    if (not isinstance(value, list) or len(value) != DIMENSIONS
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)
            or not any(value)):
        raise ValueError("Expected finite, nonzero contextual embedding at 1024 dimensions")
    return [float(x) for x in value]


@dataclass(frozen=True)
class EmbeddedChunk:
    source: AlignedChunk
    embedding: tuple[float, ...]


class VoyageKnowledge:
    def __init__(self, key: str, base: str,
                 transport: Callable[[str, str, str, dict[str, Any]], dict[str, Any]] = post):
        if base not in BASES or not key.strip():
            raise ValueError("Inject the correct credential for an official endpoint")
        self._key, self._base, self._transport = key, base, transport

    def _context(self, text: str, documents: bool) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": "voyage-context-4", "inputs": [text],
            "input_type": "document" if documents else "query",
            "output_dimension": DIMENSIONS, "output_dtype": "float",
        }
        if documents:
            payload.update(enable_auto_chunking=True, chunk_size=512, chunk_overlap=0)
        response = self._transport(self._base, self._key, "contextualizedembeddings", payload)
        if response.get("model") != "voyage-context-4":
            raise ValueError("Wrong contextual embedding model")
        document = rows(response.get("data"), 1)[0]
        return rows(document.get("data"), None if documents else 1)

    def embed_pages(self, pages: list[str]) -> list[EmbeddedChunk]:
        if (not 1 <= len(pages) <= MAX_PAGES or not all(p.strip() for p in pages)
                or sum(len(page.encode("utf-8")) for page in pages) > MAX_TEXT):
            raise ValueError("Document exceeds the bounded knowledge input")
        # One contextual document retains cross-page context. No per-page embeddings.
        response = self._context(" ".join(canonical(page) for page in pages), True)
        texts: list[str] = []
        for row in response:
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Provider omitted auto-chunked source text")
            texts.append(text)
        aligned = align_chunks(pages, texts)
        return [EmbeddedChunk(source, tuple(vector(row.get("embedding"))))
                for source, row in zip(aligned, response, strict=True)]

    def embed_query(self, query: str) -> list[float]:
        if not query.strip() or len(query) > 2000:
            raise ValueError("Query exceeds the knowledge input limit")
        return vector(self._context(query, False)[0].get("embedding"))

    def rank(self, query: str, texts: list[str]) -> list[int]:
        if (not query.strip() or len(query) > 2000 or not 1 <= len(texts) <= 20
                or any(not t.strip() or len(t) > 8000 for t in texts)
                or sum(len(text.encode("utf-8")) for text in texts) > 100_000):
            raise ValueError("Rerank input exceeds the knowledge limit")
        response = self._transport(self._base, self._key, "rerank", {
            "model": "rerank-3", "query": query, "documents": texts,
            "top_k": min(3, len(texts)), "return_documents": False, "truncation": False})
        data = response.get("data")
        if not isinstance(data, list) or len(data) != min(3, len(texts)):
            raise ValueError("Unexpected reranking result count")
        indices: list[int] = []
        previous = math.inf
        for row in data:
            if not isinstance(row, dict):
                raise ValueError("Invalid reranking response")
            index, score = row.get("index"), row.get("relevance_score")
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise ValueError("Invalid reranking score")
            if (type(index) is not int or not 0 <= index < len(texts) or index in indices
                    or not math.isfinite(score)
                    or score > previous):
                raise ValueError("Invalid reranking index or score order")
            previous = score
            indices.append(index)
        return indices
