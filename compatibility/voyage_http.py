"""Small synchronous Voyage HTTP contract probe, not a production transport.

Official endpoints and wire formats are recorded in docs/compatibility/PHASE_0.md.
No Voyage Python SDK dependency, automatic retries, or response/body logging.
"""

from __future__ import annotations

import json
import math
from functools import partial
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class VoyageContractError(ValueError):
    """Only fixed safe messages belong in this exception."""


class VoyageTransportError(RuntimeError):
    def __init__(self, status_code: int | None = None):
        self.status_code = status_code
        super().__init__("Voyage request failed; response body suppressed")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an Authorization header to a redirected endpoint.
        return None


OFFICIAL_BASE_URLS = {
    "https://api.voyageai.com/v1", "https://ai.mongodb.com/v1",
    "https://us.ai.mongodb.com/v1", "https://eu.ai.mongodb.com/v1",
}


def post_json(path: str, payload: dict, api_key: str, *,
              base_url: str = "https://api.voyageai.com/v1") -> dict:
    if base_url not in OFFICIAL_BASE_URLS:
        raise VoyageContractError("Unsupported official API base URL")
    if path not in {"contextualizedembeddings", "rerank"}:
        raise VoyageContractError("Unsupported probe endpoint")
    if not api_key.strip():
        raise VoyageContractError("Voyage API key missing")
    request = Request(
        base_url + "/" + path,
        data=json.dumps(payload, allow_nan=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        # Sequential tiny synthetic probes: bounded I/O, response size, no retries.
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise VoyageContractError("Probe response exceeded size limit")
        parsed = json.loads(body)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise VoyageTransportError(status) from None
    except (URLError, TimeoutError, OSError):
        raise VoyageTransportError() from None
    except (UnicodeError, json.JSONDecodeError):
        raise VoyageContractError("Invalid JSON response") from None
    if not isinstance(parsed, dict):
        raise VoyageContractError("Expected JSON object response")
    return parsed


def ordered_items(items: object, expected_count: int | None = None) -> list[dict]:
    if not isinstance(items, list) or not items or not all(isinstance(x, dict) for x in items):
        raise VoyageContractError("Expected nonempty indexed result list")
    indices = [item.get("index") for item in items]
    if any(type(index) is not int for index in indices) or sorted(indices) != list(range(len(items))):
        raise VoyageContractError("Result indices are missing, duplicate, or noncontiguous")
    if expected_count is not None and len(items) != expected_count:
        raise VoyageContractError("Result count differs from input count")
    return sorted(items, key=lambda item: item["index"])


def validate_vector(vector: object, dimension: int) -> list:
    if not isinstance(vector, list) or len(vector) != dimension:
        raise VoyageContractError("Unexpected embedding dimension")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
        raise VoyageContractError("Embedding must contain finite numbers")
    return vector


class VoyageHTTPProbe:
    def __init__(self, api_key: str, transport: Callable = post_json, *,
                 base_url: str = "https://api.voyageai.com/v1"):
        if base_url not in OFFICIAL_BASE_URLS:
            raise VoyageContractError("Unsupported official API base URL")
        self._api_key = api_key
        self._transport = partial(post_json, base_url=base_url) if transport is post_json else transport

    def contextual(self, texts: list[str], *, documents: bool, dimension: int = 256) -> dict:
        if dimension not in {256, 512, 1024, 2048}:
            raise VoyageContractError("Unsupported dimension")
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise VoyageContractError("Expected nonempty text inputs")
        # Restrict this diagnostic to small synthetic requests, not arbitrary bulk ingestion.
        if len(texts) > 4 or sum(map(len, texts)) > 100000:
            raise VoyageContractError("Synthetic probe input limit exceeded")
        payload = {"model": "voyage-context-4", "inputs": texts,
                   "input_type": "document" if documents else "query",
                   "output_dimension": dimension, "output_dtype": "float"}
        if documents:
            payload.update(enable_auto_chunking=True, chunk_size=512, chunk_overlap=0)
        response = self._transport("contextualizedembeddings", payload, self._api_key)
        if response.get("model") != "voyage-context-4":
            raise VoyageContractError("Unexpected contextual model")
        ordered = ordered_items(response.get("data"), len(texts))
        for item in ordered:
            chunks = ordered_items(item.get("data"), None if documents else 1)
            for chunk in chunks:
                validate_vector(chunk.get("embedding"), dimension)
                if documents and (not isinstance(chunk.get("text"), str) or not chunk["text"].strip()):
                    raise VoyageContractError("Auto-chunked text is missing")
            item["data"] = chunks
        response["data"] = ordered
        return response

    def rerank(self, query: str, documents: list[str], top_k: int = 2) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise VoyageContractError("Query is required")
        if not documents or any(not isinstance(x, str) or not x.strip() for x in documents):
            raise VoyageContractError("Documents are required")
        if type(top_k) is not int or not 1 <= top_k <= len(documents) or len(documents) > 10:
            raise VoyageContractError("Invalid probe result limit")
        if len(query) + sum(map(len, documents)) > 100000:
            raise VoyageContractError("Synthetic probe input limit exceeded")
        response = self._transport("rerank", {
            "query": query, "documents": documents, "model": "rerank-3",
            "top_k": top_k, "return_documents": False, "truncation": False,
        }, self._api_key)
        rows = response.get("data")
        if not isinstance(rows, list) or len(rows) != top_k:
            raise VoyageContractError("Unexpected reranking result count")
        seen = set()
        last_score = math.inf
        for row in rows:
            if not isinstance(row, dict):
                raise VoyageContractError("Invalid reranking row")
            index, score = row.get("index"), row.get("relevance_score")
            if type(index) is not int or not 0 <= index < len(documents) or index in seen:
                raise VoyageContractError("Invalid or duplicate reranking document index")
            if type(score) not in (float, int) or not math.isfinite(score) or score > last_score:
                raise VoyageContractError("Invalid reranking score/order")
            seen.add(index)
            last_score = score
        return response
