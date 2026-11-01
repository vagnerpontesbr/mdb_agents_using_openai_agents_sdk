"""Demo curation permissions remain distinct from administrative account creation."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from compatibility.demo_auth.auth import AccessDenied
from telecom_app.curation import CurationService, Upload
from telecom_app.knowledge_publication import PublicationConflict
from tests.foundation.test_knowledge import NOW, version


def service(role="admin", owner=False):
    identity = Mock()
    identity.principal.return_value = SimpleNamespace(role=role, user_id="actor")
    publisher = Mock()
    publisher.owner_can_publish.return_value = owner
    return CurationService(identity, Mock(), publisher, Mock(), Mock(), Mock())


def test_user_cannot_upload_or_process_or_inspect_jobs():
    current = service("user")
    data = Upload(pdf_base64="JVBERi0=", document_id="doc", version_id="1", title="Source",
                  created_at=NOW, effective_from=NOW, expires_at=NOW,
                  last_reviewed_at=NOW, review_due_at=NOW)
    for operation in (lambda: current.upload("token", data),
                      lambda: current.process_next("token"), lambda: current.jobs("token")):
        with pytest.raises(AccessDenied, match="Administrator"):
            operation()
    current.ingestion.submit.assert_not_called()


def test_admin_without_owner_entitlement_cannot_request_publication():
    current = service()
    current.ingestion.db.jobs.find_one.return_value = {
        "status": "staged", "metadata": version().model_dump(mode="json")}
    with pytest.raises(AccessDenied, match="owner"):
        current.start_review("token", "a"*64)
    current.review.create.assert_not_called()


def test_owner_cannot_review_unstaged_source():
    current = service(owner=True)
    current.ingestion.db.jobs.find_one.return_value = {
        "status": "running", "metadata": version().model_dump(mode="json")}
    with pytest.raises(PublicationConflict, match="staged"):
        current.start_review("token", "a"*64)
    current.review.create.assert_not_called()


def test_search_captures_profile_language_and_keeps_server_scope(monkeypatch):
    current = service('user')
    current.identity.profile.return_value = {'locale': 'pt-BR'}
    current.voyage.embed_query.return_value = [0.1] * 1024
    retrieval = Mock(return_value='Procedimento revisado.')
    monkeypatch.setattr('telecom_app.curation.retrieve', retrieval)
    assert current.search('token', 'roteador') == 'Procedimento revisado.'
    scope = retrieval.call_args.args[3]
    assert scope.language == 'pt'
    assert scope.tenant_id == 'synthetic-telecom'
    assert scope.readers == frozenset({'synthetic-support'})
    current.identity.principal.assert_called_with('token')
