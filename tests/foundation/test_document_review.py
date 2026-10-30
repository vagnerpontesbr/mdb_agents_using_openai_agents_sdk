"""Exact native outcome binding; no mocked outcome is claimed as Engine compatibility."""

import time
from unittest.mock import Mock

import pytest

from telecom_app.document_review import DocumentReview, request_data, request_digest
from telecom_app.journey import JourneyConflict
from tests.foundation.test_knowledge import version


def test_native_approval_cannot_authorize_changed_metadata_or_job():
    v = version()
    request = request_data('a'*64, v)
    service = DocumentReview(Mock(), Mock())
    service.present = Mock(return_value={'status': 'completed', 'result': {
        'status': 'approved', 'request': request, 'request_digest': request_digest(request),
        'requester': v.approved_by, 'expires_at': time.time() + 300}})
    assert service.verified('token', 'execution', 'a'*64, v).requester == v.approved_by
    for job, candidate in [('b'*64, v), ('a'*64, version(checksum='b'*64))]:
        with pytest.raises(JourneyConflict):
            service.verified('token', 'execution', job, candidate)
    service.present.return_value['result']['status'] = 'rejected'
    with pytest.raises(JourneyConflict):
        service.verified('token', 'execution', 'a'*64, v)


def test_bson_roundtrip_preserves_reviewed_digest():
    from bson import BSON
    from bson.codec_options import CodecOptions

    from telecom_app.knowledge import Version

    v = version(created_at=version().created_at.replace(microsecond=123456))
    stored = BSON.encode(v.model_dump()).decode(codec_options=CodecOptions(tz_aware=True))
    assert Version.model_validate(stored).approval_digest() == v.approval_digest()
