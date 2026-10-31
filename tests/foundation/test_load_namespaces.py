"""An explicit load process cannot silently write demo namespaces, or vice versa."""

from unittest.mock import Mock

import pytest

from telecom_app.ingestion import MongoIngestion
from telecom_app.knowledge_authority import MongoKnowledgeAuthority
from telecom_app.knowledge_cache import MongoCandidateCache
from telecom_app.knowledge_mongo import MongoKnowledgeReader


@pytest.mark.parametrize("factory,domain", [
    (MongoIngestion, "ingestion"),
    (MongoKnowledgeAuthority, "knowledge"),
    (MongoKnowledgeReader, "knowledge"),
    (lambda db, **kw: MongoCandidateCache(db, Mock(), **kw), "knowledge"),
])
def test_load_selection_is_explicit_and_cannot_cross_environments(factory, domain):
    demo, load, unknown = Mock(), Mock(), Mock()
    demo.name = "telecom_demo_" + domain
    load.name = "telecom_load_" + domain
    unknown.name = "untrusted_database"
    factory(demo)
    factory(load, load_environment=True)
    for database, options in ((load, {}), (demo, {"load_environment": True}),
                              (unknown, {"load_environment": True}),
                              (load, {"load_environment": "true"})):
        with pytest.raises(ValueError):
            factory(database, **options)
