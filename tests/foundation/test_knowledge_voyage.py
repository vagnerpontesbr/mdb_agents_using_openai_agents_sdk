"""Wire contracts and denied transport behavior; no paid requests in CI."""

import math
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import pytest

from telecom_app.knowledge_voyage import (
    ProviderUnavailable,
    VoyageKnowledge,
    post,
    vector,
)

BASE = "https://ai.mongodb.com/v1"


def contextual(text="Check optical cable."):
    return {"model": "voyage-context-4", "data": [{"index": 0, "data": [
        {"index": 0, "text": text, "embedding": [0.1]*1024}]}]}


def test_contextual_document_and_query_use_same_profile_and_real_auto_chunk_text():
    transport = Mock(return_value=contextual())
    client = VoyageKnowledge("synthetic", BASE, transport)
    chunks = client.embed_pages(["Check optical cable."])
    assert chunks[0].source.pages == (1,)
    payload = transport.call_args.args[3]
    assert payload["inputs"] == ["Check optical cable."]
    assert payload["enable_auto_chunking"] and payload["output_dimension"] == 1024
    assert payload["input_type"] == "document" and payload["chunk_overlap"] == 0
    assert len(client.embed_query("optical cable")) == 1024
    assert transport.call_args.args[3]["input_type"] == "query"
    assert "enable_auto_chunking" not in transport.call_args.args[3]


@pytest.mark.parametrize("bad", [[], [0.0]*1024, [True]*1024, [math.nan]*1024, [0.1]*256])
def test_invalid_vectors_are_not_indexable(bad):
    with pytest.raises(ValueError):
        vector(bad)


def test_duplicate_response_indices_and_wrong_model_are_rejected():
    for response in (contextual() | {"model": "voyage-4"},
                     {"model": "voyage-context-4", "data": [contextual()["data"][0]]*2}):
        client = VoyageKnowledge("synthetic", BASE, Mock(return_value=response))
        with pytest.raises(ValueError):
            client.embed_query("optical")


def test_document_bounds_are_checked_before_provider_call():
    transport = Mock()
    client = VoyageKnowledge("synthetic", BASE, transport)
    for pages in (["page"]*11, ["x"*60_001], ["🙂"*15_001], [""]):
        with pytest.raises(ValueError):
            client.embed_pages(pages)
    transport.assert_not_called()


def test_reranker_returns_only_known_unique_indices_and_does_not_truncate():
    transport = Mock(return_value={"data": [
        {"index": 1, "relevance_score": .9}, {"index": 0, "relevance_score": .2}]})
    client = VoyageKnowledge("synthetic", BASE, transport)
    assert client.rank("query", ["first", "second"]) == [1, 0]
    assert transport.call_args.args[3]["truncation"] is False
    transport.return_value["data"][1]["index"] = 1
    with pytest.raises(ValueError):
        client.rank("query", ["first", "second"])


def test_http_denial_is_sanitized_without_retry_or_redirect_following():
    opener = Mock()
    opener.open.side_effect = HTTPError(BASE, 429, "sensitive-provider-detail", {}, None)
    with patch("telecom_app.knowledge_voyage.build_opener", return_value=opener):
        with pytest.raises(ProviderUnavailable) as raised:
            post(BASE, "synthetic", "rerank", {})
    assert "sensitive" not in str(raised.value)
    opener.open.assert_called_once()
    with pytest.raises(ValueError):
        post("https://untrusted.invalid", "synthetic", "rerank", {})
