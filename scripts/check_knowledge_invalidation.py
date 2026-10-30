"""Live authoritative exclusions with deliberately stale chunk metadata; restores each field."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo import MongoClient

from telecom_app.curation import SCOPE, TENANT
from telecom_app.knowledge_authority import MongoKnowledgeAuthority
from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_search import retrieve
from telecom_app.knowledge_voyage import VoyageKnowledge


def main():
    evidence = json.loads(Path('compatibility/phase4-publication-evidence.json').read_text())
    key = evidence['version_key']
    voyage = VoyageKnowledge(os.environ['VOYAGE_API_KEY'], os.environ['VOYAGE_BASE_URL'])
    query = voyage.embed_query('optical cable red light')
    checks = []
    with MongoClient(os.environ['MONGODB_URI'], timeoutMS=15000,
                     tz_aware=True, appname='telecom-governance-probe') as operator, MongoClient(
            os.environ['KNOWLEDGE_READER_URI'], timeoutMS=15000) as runtime:
        db = operator.telecom_demo_knowledge
        original = db.document_versions.find_one({'_id': key, 'tenant_id': TENANT})
        if not original or original['status'] != 'published':
            raise ValueError('Expected the retained synthetic publication')
        reader = MongoKnowledgeReader(runtime.telecom_demo_knowledge)
        authority = MongoKnowledgeAuthority(runtime.telecom_demo_knowledge)
        for field, value, label in (
            ('status', 'revoked', 'revoked_version_excluded'),
            ('expires_at', datetime.now(UTC)-timedelta(seconds=1), 'expired_version_excluded'),
            ('review_due_at', datetime.now(UTC)-timedelta(seconds=1), 'overdue_review_excluded'),
            ('checksum', 'f'*64, 'changed_source_digest_excluded'),
            ('acl', ['another-reader'], 'changed_acl_excluded'),
        ):
            try:
                db.document_versions.update_one({'_id': key, 'tenant_id': TENANT}, {'$set': {field: value}})
                # Chunks retain their old published/eligible fields, modeling index lag.
                answer = retrieve(reader, authority, voyage, SCOPE, 'optical cable red light', query)
                assert 'SOP-OPTICAL-DEMO' not in answer
                checks.append(label)
            finally:
                db.document_versions.update_one({'_id': key, 'tenant_id': TENANT},
                                                 {'$set': {field: original[field]}})
        restored = db.document_versions.find_one({'_id': key, 'tenant_id': TENANT})
        assert restored == original
    output = {'checked_at': datetime.now(UTC).isoformat(), 'checks_passed': checks,
              'source_restored': True, 'stale_chunk_metadata_left_unchanged': True,
              'query_embedding_calls': 1, 'limitations': ['Controlled stale metadata, not a lag benchmark']}
    Path('compatibility/phase4-invalidation-evidence.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Invalidation check failed: {type(error).__name__}; details suppressed')
        raise SystemExit(1) from None
