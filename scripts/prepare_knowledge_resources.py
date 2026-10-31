"""Write a reviewable Phase 4 Atlas plan; never connect, provision or modify a database."""

import argparse
import json
from pathlib import Path

from telecom_app.knowledge_search import index_definitions

KNOWLEDGE = 'telecom_demo_knowledge'
INGESTION = 'telecom_demo_ingestion'


def privilege(database, collections, actions):
    return [{'resource': {'db': database, 'collection': name}, 'actions': actions}
            for name in collections]


def plan():
    return {
        'status': 'proposed_not_applied', 'cluster': 'OpenAI-SDK',
        'project_id': '67b385a7976edf15ecc62e06',
        'collections': {
            KNOWLEDGE: ['documents', 'document_versions', 'chunks', 'review_events', 'owners'],
            INGESTION: ['jobs', 'staged_artifacts'],
        },
        'search_indexes': [{'database': KNOWLEDGE, 'collection': 'chunks', **index}
                           for index in index_definitions()],
        'classic_indexes': [
            {'database': KNOWLEDGE, 'collection': 'document_versions',
             'name': 'tenant_document_version_revision',
             'key': {'tenant_id': 1, 'document_id': 1, 'version_id': 1, 'revision': 1},
             'unique': True},
            {'database': KNOWLEDGE, 'collection': 'chunks', 'name': 'tenant_version_chunk',
             'key': {'tenant_id': 1, 'version_key': 1, 'chunk_id': 1}, 'unique': True},
            {'database': KNOWLEDGE, 'collection': 'review_events', 'name': 'tenant_review_execution',
             'key': {'tenant_id': 1, 'execution_id': 1, 'action_digest': 1}, 'unique': True},
            {'database': INGESTION, 'collection': 'jobs', 'name': 'tenant_submission',
             'key': {'tenant_id': 1, 'submission_key': 1}, 'unique': True},
            {'database': INGESTION, 'collection': 'jobs', 'name': 'claim_available_job',
             'key': {'status': 1, 'available_at': 1, '_id': 1}},
        ],
        'runtime_roles': {
            'telecomKnowledgeReader': privilege(KNOWLEDGE,
                ['documents', 'document_versions', 'chunks', 'review_events', 'owners'], ['find']),
            'telecomKnowledgePublisher': [
                *privilege(KNOWLEDGE, ['documents', 'document_versions', 'chunks'],
                           ['find', 'insert', 'update']),
                *privilege(KNOWLEDGE, ['review_events'], ['find', 'insert']),
                *privilege(KNOWLEDGE, ['owners'], ['find']),
            ],
            'telecomIngestionWorker': privilege(INGESTION, ['jobs', 'staged_artifacts'],
                                                ['find', 'insert', 'update']),
        },
        'runtime_users': [
            {'username': 'telecom_knowledge_reader', 'role': 'telecomKnowledgeReader'},
            {'username': 'telecom_knowledge_publisher', 'role': 'telecomKnowledgePublisher'},
            {'username': 'telecom_ingestion_worker', 'role': 'telecomIngestionWorker'},
        ],
        'constraints': [
            'Every runtime identity is scoped to the existing OpenAI-SDK cluster.',
            'Inject generated credentials privately; no existing identity grants are expanded.',
            'No runtime role may create indexes, delete data or access Engine-managed databases.',
            'Operator-only owner registry provisioning; publisher cannot grant itself ownership.',
            'Review events record domain evidence bound to native Engine review, not a new approval engine.',
            'Search readiness, schema validators and allowed/denied role probes gate application enablement.',
            'No shared Engine policy or tool allowlist change is authorized by this database plan.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as output:
        json.dump(plan(), output, indent=2)
        output.write('\n')
    print('Wrote proposed Atlas resources; no remote changes made')


if __name__ == '__main__':
    main()
