"""A cache hit cannot replace current source authorization or release checks."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock

import pytest

from telecom_app.knowledge_cache import MongoCandidateCache, scope_key
from telecom_app.knowledge_search import retrieve
from tests.foundation.test_knowledge import NOW, SCOPE, authority, retrieval_fixture


def test_cached_source_still_uses_current_reranker_and_release_authority():
    v, chunk, reader, reranker = retrieval_fixture()
    cache = Mock()
    cache.lookup.return_value = [chunk]
    answer = retrieve(reader, authority(v), reranker, SCOPE, "router", [.1]*1024,
                      lambda: NOW, cache=cache)
    assert chunk.text in answer
    reader.search.assert_not_called()
    reranker.rank.assert_called_once_with("router", [chunk.text])


def test_stale_cached_reference_discards_set_and_refreshes_search():
    v, chunk, reader, reranker = retrieval_fixture()
    cache = Mock()
    cache.lookup.return_value = [chunk.model_copy(update={"revision": 9})]
    assert chunk.text in retrieve(reader, authority(v), reranker, SCOPE, "router", [.1]*1024,
                                 lambda: NOW, cache=cache)
    reader.search.assert_called_once()


def test_cache_failure_falls_back_without_disabling_governance():
    v, _, reader, reranker = retrieval_fixture()
    cache = Mock()
    cache.lookup.side_effect = RuntimeError("Cache unavailable")
    cache.store.side_effect = RuntimeError("Write unavailable")
    auth = authority(v)
    auth.owner_active.return_value = False
    assert "No currently approved" in retrieve(reader, auth, reranker, SCOPE, "router",
                                               [.1]*1024, lambda: NOW, cache=cache)
    reranker.rank.assert_not_called()


def test_cached_source_revoked_during_rerank_is_not_released():
    v, chunk, reader, reranker = retrieval_fixture()
    cache = Mock()
    cache.lookup.return_value = [chunk]
    def revoke(*args):
        reader.version.return_value = v.model_copy(update={"status": "revoked"})
        return [0]
    reranker.rank.side_effect = revoke
    assert "changed before release" in retrieve(reader, authority(v), reranker, SCOPE,
                                               "router", [.1]*1024, lambda: NOW, cache=cache)


def test_cache_scope_hash_covers_tenant_acl_and_equipment():
    base = scope_key(SCOPE)
    for field, value in (("tenant_id", "other"), ("readers", frozenset({"other"})),
                         ("firmware_range", "1.x"), ("product", "other"), ("region", "other")):
        assert scope_key(replace(SCOPE, **{field: value})) != base


def test_fixed_slots_and_source_expiry_bound_storage():
    v, chunk, reader, _ = retrieval_fixture()
    reader.version.return_value = v.model_copy(update={"expires_at": NOW+timedelta(minutes=2)})
    db = Mock(name="database")
    db.name = "telecom_demo_knowledge"
    db.with_options.return_value = db
    cache = MongoCandidateCache(db, reader)
    for i in range(300):
        cache.store(SCOPE, f"query-{i}", [.1]*1024, [chunk], NOW)
    writes = db.retrieval_cache.replace_one.call_args_list
    assert len({call.args[0]["_id"] for call in writes}) <= 128
    assert all(call.args[1]["expires_at"] == NOW+timedelta(minutes=2) for call in writes)
    assert all("text" not in call.args[1] and "query" not in call.args[1] for call in writes)


@pytest.mark.parametrize("change", [
    {"expires_at": NOW}, {"created_at": NOW+timedelta(seconds=1)},
    {"sources": []}, {"query_sha256": "changed"},
])
def test_stale_index_overwritten_or_expired_slot_is_a_miss(change):
    _, chunk, reader, _ = retrieval_fixture()
    db = Mock()
    db.name = "telecom_demo_knowledge"
    db.with_options.return_value = db
    cache = MongoCandidateCache(db, reader)
    cache.store(SCOPE, "router", [.1]*1024, [chunk], NOW)
    row = db.retrieval_cache.replace_one.call_args.args[1]
    db.retrieval_cache.aggregate.return_value = [{**row, "score": 1.0}]
    db.retrieval_cache.find_one.return_value = {**row, **change}
    assert cache.lookup(SCOPE, "router", [.1]*1024, NOW) is None


def test_duplicate_cached_candidates_fall_back_to_valid_search():
    v, chunk, reader, reranker = retrieval_fixture()
    cache = Mock()
    cache.lookup.return_value = [chunk, chunk]
    answer = retrieve(reader, authority(v), reranker, SCOPE, "router", [.1]*1024,
                      lambda: NOW, cache=cache)
    assert chunk.text in answer
    reader.search.assert_called_once()
