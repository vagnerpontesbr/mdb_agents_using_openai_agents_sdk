"""Deterministic governance and retrieval contracts; no remote search claims."""

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from telecom_app.knowledge import Scope, Version, align_chunks, assess, submission_key
from telecom_app.knowledge_search import Candidate, hybrid_pipeline, index_definitions, retrieve

NOW = datetime(2026, 10, 30, tzinfo=UTC)
SCOPE = Scope("synthetic-telecom", frozenset({"synthetic-support"}), "FiberBox", "demo", "2.x")


def version(**changes):
    data = dict(
        tenant_id=SCOPE.tenant_id, document_id="SOP-ONT", version_id="2", revision=1,
        title="Current optical procedure", information_owner="network-operations",
        created_at=NOW-timedelta(days=90), ingested_at=NOW,
        effective_from=NOW-timedelta(days=30), expires_at=NOW+timedelta(days=90),
        last_reviewed_at=NOW-timedelta(days=10), review_due_at=NOW+timedelta(days=30),
        reviewed_by="reviewer", approved_by="owner", approved_at=NOW-timedelta(days=5),
        source_uri="fixture://SOP-ONT/2", source_system="synthetic-register", checksum="a"*64,
        classification="internal-demo", acl=("synthetic-support",), language="en",
        product="FiberBox", region="demo", firmware_range="2.x", status="published",
        business_impact="high", change_rate="high")
    return Version(**(data | changes))


def authority(v):
    auth = Mock()
    auth.owner_active.return_value = True
    digest = v.approval_digest()
    auth.approval_valid.side_effect = lambda candidate, value: value == digest
    auth.source_verified.return_value = True
    auth.current_version.return_value = (v.version_id, v.revision)
    auth.conflict_confirmed.return_value = False
    return auth


def test_current_and_obsolete_risk_are_independent_of_recent_ingestion():
    current = version()
    assert assess(current, SCOPE, NOW, authority(current)).score == 10
    old = version(version_id="1", expires_at=NOW-timedelta(days=1),
                  review_due_at=NOW-timedelta(days=1), status="superseded", superseded_by="2")
    result = assess(old, SCOPE, NOW, authority(old))
    assert result.score == 80 and result.band == "critical" and not result.eligible


@pytest.mark.parametrize("changes,blocker", [
    ({"expires_at": NOW}, "expired"), ({"review_due_at": NOW}, "review_overdue"),
    ({"effective_from": NOW+timedelta(days=1)}, "not_effective"),
    ({"status": "revoked"}, "not_published"),
    ({"acl": ("another-reader",)}, "access_denied"),
    ({"tenant_id": "other"}, "access_denied"),
    ({"firmware_range": "1.x"}, "not_applicable"),
    ({"approved_at": NOW+timedelta(days=1)}, "future_review_or_approval"),
])
def test_hard_exclusions_cannot_be_overridden_by_score(changes, blocker):
    v = version(**changes)
    result = assess(v, SCOPE, NOW, authority(v))
    assert not result.eligible and blocker in result.blockers


def test_exact_approval_binds_checksum_validity_acl_and_governance_revision():
    original = version()
    auth = authority(original)
    for changes in ({"checksum": "b"*64}, {"expires_at": NOW+timedelta(days=180)},
                    {"acl": ("synthetic-support", "extra")}, {"revision": 2}):
        changed = version(**changes)
        assert "unverified" in assess(changed, SCOPE, NOW, auth).blockers
    auth.owner_active.return_value = False
    assert "owner_unresolved" in assess(original, SCOPE, NOW, auth).blockers


def test_source_and_review_chronology_reject_naive_dates_and_reversed_intervals():
    for changes in ({"created_at": NOW.replace(tzinfo=None)},
                    {"review_due_at": NOW-timedelta(days=20)},
                    {"expires_at": NOW-timedelta(days=60)}):
        with pytest.raises(ValueError):
            version(**changes)


def test_normalized_provenance_spans_pages_without_guessing_repeated_or_changed_text():
    chunks = align_chunks(["Header\nCheck optical cable.", "Header\nContact support."],
                          ["Check optical cable.", "optical cable. Header Contact",
                           "Header", "The model rewrote this text."])
    assert chunks[0].pages == (1,)
    assert chunks[1].pages == (1, 2)
    assert chunks[2].pages == chunks[3].pages == ()
    assert not chunks[2].page_known
    with pytest.raises(ValueError):
        align_chunks(["a"]*11, ["a"])


def test_submission_identity_changes_with_tenant_content_or_metadata():
    first = submission_key("tenant", "doc", "1", "a"*64, "b"*64)
    assert first == submission_key("tenant", "doc", "1", "a"*64, "b"*64)
    assert len({first, submission_key("other", "doc", "1", "a"*64, "b"*64),
                submission_key("tenant", "doc", "1", "c"*64, "b"*64),
                submission_key("tenant", "doc", "1", "a"*64, "d"*64)}) == 4


def test_native_fusion_filters_both_branches_and_indexes_cover_filters():
    pipeline = hybrid_pipeline(SCOPE, "optical cable", [0.1]*1024, NOW)
    branches = pipeline[0]["$rankFusion"]["input"]["pipelines"]
    lexical = branches["lexical"][0]["$search"]["compound"]["filter"]
    vector = branches["semantic"][0]["$vectorSearch"]["filter"]["$and"]
    assert {"acl": {"$in": ["synthetic-support"]}} in vector
    assert {"expires_at": {"$gt": NOW}} in vector
    assert {"tenant_id": {"$eq": "synthetic-telecom"}} in vector
    assert {"range": {"path": "review_due_at", "gt": NOW}} in lexical
    assert {"equals": {"path": "tenant_id", "value": "synthetic-telecom"}} in lexical
    assert branches["lexical"][-1] == {"$limit": 20}
    definitions = index_definitions()
    indexed = {field["path"] for field in definitions[1]["definition"]["fields"]}
    assert set().union(*(item.keys() for item in vector)) <= indexed
    with pytest.raises(ValueError):
        hybrid_pipeline(SCOPE, "query", [0.1]*256, NOW)


def retrieval_fixture():
    v = version()
    text = "Check the regional incident before restarting the router."
    chunk = Candidate(chunk_id="c1", version_key="v2", revision=1, text=text,
                      text_sha256=hashlib.sha256(text.encode()).hexdigest(), pages=(2,))
    reader = Mock()
    reader.search.return_value = [chunk]
    reader.version.return_value = v
    reader.chunk.return_value = chunk
    reranker = Mock()
    reranker.rank.return_value = [0]
    return v, chunk, reader, reranker


def test_citation_is_exact_and_current_authority_overrides_stale_search_index():
    v, chunk, reader, reranker = retrieval_fixture()
    auth = authority(v)
    assert retrieve(reader, auth, reranker, SCOPE, "router", [0.1]*1024, lambda: NOW) == (
        chunk.text+"\n[SOP-ONT, version 2, pages 2]")
    auth.current_version.return_value = ("3", 2)
    reranker.reset_mock()
    result = retrieve(reader, auth, reranker, SCOPE, "router", [0.1]*1024, lambda: NOW)
    assert "No currently approved" in result
    reranker.rank.assert_not_called()


def test_revocation_during_reranking_prevents_answer_release():
    v, _, reader, reranker = retrieval_fixture()
    auth = authority(v)
    def revoke(*args):
        reader.version.return_value = v.model_copy(update={"status": "revoked"})
        return [0]
    reranker.rank.side_effect = revoke
    assert "changed before release" in retrieve(reader, auth, reranker, SCOPE,
                                                "router", [0.1]*1024, lambda: NOW)


def test_forged_index_text_is_not_sent_to_reranker():
    v, chunk, reader, reranker = retrieval_fixture()
    reader.search.return_value = [chunk.model_copy(update={"text": "Untrusted replacement"})]
    assert "No currently approved" in retrieve(reader, authority(v), reranker, SCOPE,
                                               "router", [0.1]*1024, lambda: NOW)
    reranker.rank.assert_not_called()


def test_retrieval_uses_composite_chunk_identity():
    v, chunk, reader, reranker = retrieval_fixture()
    retrieve(reader, authority(v), reranker, SCOPE, "router", [0.1]*1024, lambda: NOW)
    reader.chunk.assert_called_with(SCOPE.tenant_id, chunk.version_key,
                                    chunk.chunk_id, chunk.revision)


def test_oversized_procedure_abstains_instead_of_cutting_instructions():
    v, chunk, reader, reranker = retrieval_fixture()
    text = "x" * 7500
    chunk = chunk.model_copy(update={"text": text,
                                    "text_sha256": hashlib.sha256(text.encode()).hexdigest()})
    reader.search.return_value = [chunk]
    reader.chunk.return_value = chunk
    result = retrieve(reader, authority(v), reranker, SCOPE, "router", [0.1]*1024, lambda: NOW)
    assert result == "The approved procedure exceeds the response limit. Contact support."


def test_same_chunk_id_in_distinct_versions_does_not_collide():
    v, chunk, reader, reranker = retrieval_fixture()
    other = version(document_id="SOP-OTHER")
    second = chunk.model_copy(update={"version_key": "other-version"})
    reader.search.return_value = [chunk, second]
    reader.chunk.side_effect = lambda tenant, key, chunk_id, revision: {
        chunk.version_key: chunk, second.version_key: second}[key]
    reader.version.side_effect = lambda tenant, key: {
        chunk.version_key: v, second.version_key: other}[key]
    auth = authority(v)
    auth.approval_valid.side_effect = lambda candidate, digest: (
        digest == candidate.approval_digest())
    reranker.rank.return_value = [0, 1]
    result = retrieve(reader, auth, reranker, SCOPE, "router", [0.1]*1024, lambda: NOW)
    assert "[SOP-ONT, version 2, pages 2]" in result
    assert "[SOP-OTHER, version 2, pages 2]" in result
