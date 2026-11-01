"""Language/source lineage is governance, independent of search relevance."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from telecom_app.knowledge import assess
from telecom_app.knowledge_authority import MongoKnowledgeAuthority, version_key
from telecom_app.knowledge_schema import knowledge_validators
from tests.foundation.test_knowledge import NOW, SCOPE, authority, version


def original_authority(original):
    database = Mock()
    database.name = "telecom_demo_knowledge"
    database.with_options.return_value = database
    database.document_versions.find_one.return_value = original.model_dump()
    current = MongoKnowledgeAuthority(database)
    for name in ("owner_active", "approval_valid", "source_verified"):
        setattr(current, name, Mock(return_value=True))
    current.current_version = Mock(return_value=(original.version_id, original.revision))
    current.conflict_confirmed = Mock(return_value=False)
    return current, database


def test_legacy_approval_digest_and_serialization_are_unchanged():
    original = version()
    assert original.approval_digest() == (
        "7c86d76018b69140c17ed918cbb00d24c7374c6ad01cad1fb4cd45064ff823a8")
    assert "translation_of" not in original.model_dump()
    assert "translation_of" not in original.model_dump(mode="json")
    translated = version(language="pt", translation_of="b" * 64)
    assert translated.model_dump()["translation_of"] == "b" * 64
    assert translated.approval_digest() != version(language="pt").approval_digest()


@pytest.mark.parametrize("language", ["pt", "es"])
def test_translated_source_requires_both_documents_to_be_current_and_authorized(language):
    original = version()
    translated = version(document_id="SOP-" + language, language=language,
                         translation_of=version_key(original))
    current, database = original_authority(original)
    scope = replace(SCOPE, language=language)
    assert current.translation_valid(translated, scope, NOW)
    query = database.document_versions.find_one.call_args.args[0]
    assert query == {"tenant_id": SCOPE.tenant_id, "_id": version_key(original)}
    assert database.document_versions.find_one.call_args.kwargs["max_time_ms"] == 15000
    current.owner_active.return_value = False
    assert not current.translation_valid(translated, scope, NOW)


@pytest.mark.parametrize("changes", [
    {"status": "revoked"}, {"expires_at": NOW}, {"review_due_at": NOW},
    {"acl": ("another-reader",)}, {"tenant_id": "other"},
    {"translation_of": "a" * 64}, {"language": "pt"},
])
def test_unavailable_or_chained_original_blocks_translation(changes):
    original = version(**changes)
    translated = version(document_id="SOP-PT", language="pt",
                         translation_of=version_key(original))
    current, _ = original_authority(original)
    assert not current.translation_valid(translated, replace(SCOPE, language="pt"), NOW)


def test_replaced_missing_and_mismatched_original_block_translation():
    original = version()
    translated = version(document_id="SOP-PT", language="pt",
                         translation_of=version_key(original))
    current, database = original_authority(original)
    current.current_version.return_value = ("new", 2)
    assert not current.translation_valid(translated, replace(SCOPE, language="pt"), NOW)
    current.current_version.return_value = (original.version_id, original.revision)
    database.document_versions.find_one.return_value = None
    assert not current.translation_valid(translated, replace(SCOPE, language="pt"), NOW)
    database.document_versions.find_one.return_value = version(version_id="other").model_dump()
    assert not current.translation_valid(translated, replace(SCOPE, language="pt"), NOW)


def test_assessment_keeps_language_filter_and_consults_lineage_only_when_declared():
    translated = version(language="pt", translation_of="b" * 64)
    auth = authority(translated)
    auth.translation_valid.return_value = False
    result = assess(translated, replace(SCOPE, language="pt"), NOW, auth)
    assert "translation_source_invalid" in result.blockers
    auth.translation_valid.return_value = True
    assert assess(translated, replace(SCOPE, language="pt"), NOW, auth).eligible
    assert "not_applicable" in assess(translated, SCOPE, NOW, auth).blockers
    primary = version(language="es")
    auth = authority(primary)
    assert assess(primary, replace(SCOPE, language="es"), NOW, auth).eligible
    auth.translation_valid.assert_not_called()


def test_additive_storage_schema_preserves_strictness_and_embedding_dimensions():
    schemas = knowledge_validators()
    metadata = schemas["document_versions"]["$and"][0]["$jsonSchema"]
    chunks = schemas["chunks"]["$jsonSchema"]
    assert metadata["properties"]["language"]["enum"] == ["en", "pt", "es"]
    assert chunks["properties"]["language"]["enum"] == ["en", "pt", "es"]
    assert "translation_of" not in metadata["required"]
    assert metadata["additionalProperties"] is False
    assert chunks["properties"]["embedding"]["minItems"] == 1024


def test_cached_translation_is_not_released_after_original_revocation():
    import hashlib

    from telecom_app.knowledge_search import Candidate, retrieve

    original = version()
    translated = version(document_id="SOP-PT", language="pt",
                         translation_of=version_key(original))
    current, database = original_authority(original)
    text = "Verifique a alimentação do roteador."
    candidate = Candidate(chunk_id="0", version_key=version_key(translated), revision=1,
                          text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                          pages=(1,))
    reader = Mock()
    reader.chunk.return_value = candidate
    reader.version.return_value = translated
    cache = Mock()
    cache.lookup.return_value = [candidate]
    reranker = Mock()

    def revoke(*args):
        database.document_versions.find_one.return_value = original.model_copy(
            update={"status": "revoked"}).model_dump()
        return [0]

    reranker.rank.side_effect = revoke
    output = retrieve(reader, current, reranker, replace(SCOPE, language="pt"),
                      "roteador", [0.1] * 1024, clock=lambda: NOW, cache=cache)
    assert text not in output
    assert "changed before release" in output
    reader.search.assert_not_called()
