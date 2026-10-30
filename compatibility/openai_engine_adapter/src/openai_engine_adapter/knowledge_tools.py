"""Engine-mediated knowledge tools; only scoped domain credentials enter the Tool Pod."""

from functools import lru_cache
import os
from urllib.parse import urlsplit

from pydantic import Field
from agent_engine_runner_shared.context import get_current_user_id

from .journey_domain import BusinessResult, Contract, subject


class KnowledgeQuery(Contract):
    query: str = Field(min_length=1, max_length=2000)


class IngestionQuery(Contract):
    job_id: str = Field(pattern=r"^[a-f0-9]{64}$")


@lru_cache(maxsize=2)
def domain_client(variable, username):
    from pymongo import MongoClient
    uri = os.environ[variable]
    parsed = urlsplit(uri)
    if (parsed.scheme != 'mongodb+srv' or parsed.hostname != 'openai-sdk.qrmdk.mongodb.net'
            or parsed.username != username):
        raise ValueError('Unexpected domain credential')
    # Eight admitted backend requests; reuse one lazily opened client per Tool Pod/domain.
    return MongoClient(uri, maxPoolSize=8, minPoolSize=0, timeoutMS=15000,
                       waitQueueTimeoutMS=2000, appname='telecom-engine-knowledge')


def search_knowledge(query):
    from .knowledge_domain.knowledge import Scope
    from .knowledge_domain.knowledge_authority import MongoKnowledgeAuthority
    from .knowledge_domain.knowledge_mongo import MongoKnowledgeReader
    from .knowledge_domain.knowledge_search import retrieve
    from .knowledge_domain.knowledge_voyage import VoyageKnowledge
    user = subject(get_current_user_id())
    database = domain_client('KNOWLEDGE_READER_URI', 'telecom_knowledge_reader').telecom_demo_knowledge
    voyage = VoyageKnowledge(os.environ['KNOWLEDGE_VOYAGE_KEY'], os.environ['KNOWLEDGE_VOYAGE_BASE'])
    scope = Scope('synthetic-telecom', frozenset({'synthetic-support'}), 'FiberBox', 'demo', '2.x')
    text = retrieve(MongoKnowledgeReader(database), MongoKnowledgeAuthority(database), voyage,
                    scope, query, voyage.embed_query(query), max_response_chars=1800)
    return BusinessResult(kind='technical', account_ref=user, reference='knowledge-current', text=text).model_dump()


def request_ingestion(job_id):
    from .knowledge_domain.ingestion import MongoIngestion
    user = subject(get_current_user_id())
    knowledge = domain_client('KNOWLEDGE_READER_URI', 'telecom_knowledge_reader').telecom_demo_knowledge
    if not knowledge.owners.find_one({'tenant_id': 'synthetic-telecom', 'active': True, 'user_ids': user}):
        raise ValueError('Registered document owner required for the agent ingestion tool')
    store = MongoIngestion(domain_client('INGESTION_MONGODB_URI',
                                        'telecom_ingestion_worker').telecom_demo_ingestion)
    job = store.db.jobs.find_one({'_id': job_id, 'tenant_id': 'synthetic-telecom'})
    if job is None or not job.get('metadata'):
        raise ValueError('Upload the PDF through the curator interface first')
    key = store.submit(job['tenant_id'], job['document_id'], job['version_id'],
                       job['metadata_digest'], store.source(job), scanned=job['scanned'],
                       metadata=job['metadata'])
    return BusinessResult(kind='technical', account_ref=user, reference=key,
        text=f"The PDF ingestion request is registered as {key}. Current status: {job['status']}. "
             "An administrator runs the separate worker; this action does not publish the PDF.").model_dump()
