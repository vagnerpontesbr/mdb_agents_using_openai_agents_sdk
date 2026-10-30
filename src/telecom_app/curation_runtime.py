"""Separate scoped clients for the demo's co-located service-domain adapters."""

import os
from typing import Any
from urllib.parse import urlsplit

from pymongo import MongoClient

from .config import CONCURRENCY, Settings
from .curation import CurationService
from .document_review import DocumentReview
from .identity import IdentityService
from .ingestion import MongoIngestion
from .journey import EngineAPI
from .knowledge_mongo import MongoKnowledgeReader
from .knowledge_publication import MongoKnowledgePublisher
from .knowledge_voyage import VoyageKnowledge


def configure(
    identity: IdentityService,
) -> tuple[CurationService, list[MongoClient[dict[str, Any]]]]:
    clients: list[MongoClient[dict[str, Any]]] = []
    try:
        for variable, user in (
            ("INGESTION_MONGODB_URI", "telecom_ingestion_worker"),
            ("KNOWLEDGE_PUBLISHER_URI", "telecom_knowledge_publisher"),
            ("KNOWLEDGE_READER_URI", "telecom_knowledge_reader"),
        ):
            uri = os.environ[variable]
            Settings(mongodb_uri=uri)
            if urlsplit(uri).username != user:
                raise ValueError("Expected the dedicated domain identity")
            # At most eight admitted HTTP requests; reuse one client per domain.
            clients.append(
                MongoClient(
                    uri,
                    maxPoolSize=CONCURRENCY,
                    minPoolSize=0,
                    timeoutMS=15000,
                    waitQueueTimeoutMS=2000,
                    appname="telecom-" + user,
                )
            )
        return CurationService(
            identity,
            MongoIngestion(clients[0].telecom_demo_ingestion),
            MongoKnowledgePublisher(clients[1].telecom_demo_knowledge),
            MongoKnowledgeReader(clients[2].telecom_demo_knowledge),
            DocumentReview(identity, EngineAPI()),
            VoyageKnowledge(os.environ["VOYAGE_API_KEY"], os.environ["VOYAGE_BASE_URL"]),
        ), clients
    except Exception:
        for client in clients:
            client.close()
        raise RuntimeError("Knowledge configuration unavailable; details suppressed") from None
