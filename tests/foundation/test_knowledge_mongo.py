"""Adapter boundary tests; database enforcement is checked separately against Atlas."""

from unittest.mock import Mock

import pytest

from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_schema import bson_schema, knowledge_validators


def reader_fixture():
    database = Mock()
    database.name = "telecom_demo_knowledge"
    database.with_options.return_value = database
    return MongoKnowledgeReader(database), database


def test_chunk_lookup_binds_tenant_version_chunk_and_revision():
    reader, database = reader_fixture()
    database.chunks.find_one.return_value = None
    assert reader.chunk("tenant-a", "version-2", "chunk-1", 3) is None
    args = database.chunks.find_one.call_args
    assert args.args[0] == {"tenant_id": "tenant-a", "version_key": "version-2",
                            "chunk_id": "chunk-1", "revision": 3}
    assert args.args[1]["_id"] == 0
    assert args.kwargs["max_time_ms"] == 15000


def test_version_lookup_is_tenant_bound_and_rejects_malformed_storage():
    reader, database = reader_fixture()
    database.document_versions.find_one.return_value = {"tenant_id": "tenant-a"}
    with pytest.raises(ValueError):
        reader.version("tenant-a", "version-2")
    assert database.document_versions.find_one.call_args.args[0] == {
        "tenant_id": "tenant-a", "_id": "version-2"}


def test_reader_refuses_other_database_and_preserves_aware_dates():
    reader, database = reader_fixture()
    assert database.with_options.call_args.kwargs["codec_options"].tz_aware is True
    database.name = "engine-memory"
    with pytest.raises(ValueError, match="Unexpected"):
        MongoKnowledgeReader(database)


def test_storage_schema_preserves_dates_and_rejects_unknown_translation():
    validators = knowledge_validators()
    version = validators["document_versions"]["$and"][0]["$jsonSchema"]
    assert version["properties"]["created_at"] == {"bsonType": "date"}
    assert version["additionalProperties"] is False
    chunk = validators["chunks"]["$jsonSchema"]
    assert chunk["properties"]["embedding"]["minItems"] == 1024
    assert chunk["properties"]["pages"]["uniqueItems"] is True
    with pytest.raises(ValueError, match="Unsupported"):
        bson_schema({"$ref": "not-supported"})
