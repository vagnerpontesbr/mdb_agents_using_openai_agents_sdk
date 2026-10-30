"""Staging boundaries; transactional queue behavior has a separate live Atlas probe."""

import copy
import hashlib
from unittest.mock import Mock

import pytest

from telecom_app.ingestion import MongoIngestion
from telecom_app.ingestion_worker import validate_staged
from telecom_app.knowledge_search import PROFILE


def staged():
    text = "Check the optical cable."
    return {"checksum": "a"*64, "pages": [text], "ocr": False,
            "parser_version": "docling-2.143.1", "embedding_profile": PROFILE,
            "chunks": [{"text": text, "pages": [1],
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "embedding": [0.1]*1024}]}


def test_complete_staging_contract_accepts_aligned_source():
    validate_staged(staged(), "a"*64, False)


@pytest.mark.parametrize("change", ["checksum", "ocr", "page", "vector", "text", "hash"])
def test_staging_rejects_forged_provenance_and_wrong_embedding(change):
    result = copy.deepcopy(staged())
    if change == "checksum":
        result["checksum"] = "b"*64
    elif change == "ocr":
        result["ocr"] = True
    elif change == "page":
        result["chunks"][0]["pages"] = [2]
    elif change == "vector":
        result["chunks"][0]["embedding"] = [float("nan")]*1024
    elif change == "text":
        result["chunks"][0]["text"] = "Invented procedure"
    else:
        result["chunks"][0]["text_sha256"] = "b"*64
    with pytest.raises(ValueError):
        validate_staged(result, "a"*64, False)


def test_bad_submission_cannot_reach_database():
    database = Mock()
    database.name = "telecom_demo_ingestion"
    store = MongoIngestion(database)
    with pytest.raises(ValueError):
        store.submit("tenant", "doc", "1", "a"*64, b"not a PDF")
    database.with_options.return_value.client.start_session.assert_not_called()
    database.name = "telecom_demo_knowledge"
    with pytest.raises(ValueError):
        MongoIngestion(database)


def test_unknown_page_does_not_allow_invented_source_text():
    result = staged()
    text = "Invented instruction absent from the extracted PDF."
    result["chunks"][0].update(text=text, pages=[],
                               text_sha256=hashlib.sha256(text.encode()).hexdigest())
    with pytest.raises(ValueError, match="provenance"):
        validate_staged(result, "a"*64, False)
