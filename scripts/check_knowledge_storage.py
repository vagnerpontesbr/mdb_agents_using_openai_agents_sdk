"""Apply core knowledge validators and probe them using rolled-back synthetic writes.

Only empty collections or an identical existing validator are accepted. No user
data is migrated and no native approval or hosted configuration is changed.
"""

import argparse
import copy
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure

from telecom_app.knowledge import Scope, Version
from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_schema import knowledge_validators
from telecom_app.knowledge_search import PROFILE, hybrid_pipeline


def specimens():
    now = datetime.now(UTC)
    marker = 'synthetic-storage-' + uuid4().hex
    version = Version(
        tenant_id=marker, document_id='SOP-STORAGE-PROBE', version_id='1', revision=1,
        title='Synthetic storage validation', information_owner='synthetic-owner',
        created_at=now-timedelta(days=2), ingested_at=now,
        effective_from=now-timedelta(days=1), expires_at=now+timedelta(days=2),
        last_reviewed_at=now-timedelta(days=1), review_due_at=now+timedelta(days=1),
        reviewed_by='synthetic-owner', approved_by='synthetic-owner', approved_at=now,
        source_uri='fixture://storage-probe', source_system='synthetic', checksum='a'*64,
        classification='internal-demo', acl=('synthetic-reader',), language='en',
        product='FiberBox', region='demo', firmware_range='2.x', status='draft',
        business_impact='low', change_rate='low',
    ).model_dump()
    version['_id'] = marker
    text = 'Check the optical cable before restarting the router.'
    chunk = {key: version[key] for key in ('tenant_id', 'acl', 'product', 'region',
             'firmware_range', 'language', 'status', 'effective_from', 'expires_at', 'review_due_at')}
    chunk.update(_id=marker, chunk_id='c1', version_key=marker, revision=1, text=text,
                 text_sha256=hashlib.sha256(text.encode()).hexdigest(), pages=[1],
                 embedding=[0.1]*1024, embedding_profile=PROFILE, eligible=False)
    return version, chunk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-validators', action='store_true', required=True)
    parser.parse_args()
    uri = os.environ['MONGODB_URI']
    if urlsplit(uri).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise ValueError('Unexpected cluster')
    validators = knowledge_validators()
    with MongoClient(uri, timeoutMS=15000, appname='telecom-schema-provision') as client:
        database = client.telecom_demo_knowledge
        for name, validator in validators.items():
            options = database[name].options()
            if options.get('validator') not in (None, {}, validator):
                raise ValueError('Existing validator drift')
            if options.get('validator') != validator and database[name].find_one({}, {'_id': 1}):
                raise ValueError('Nonempty collection requires a separate migration')
        for name, validator in validators.items():
            database.command('collMod', name, validator=validator,
                             validationLevel='strict', validationAction='error')
            options = database[name].options()
            assert options['validator'] == validator
            assert options['validationLevel'] == 'strict' and options['validationAction'] == 'error'
    credentials = dict(line.split('=', 1) for line in
                       Path('.env.phase4').read_text().splitlines() if line)
    version, chunk = specimens()
    checks = []
    with MongoClient('mongodb+srv://openai-sdk.qrmdk.mongodb.net/',
                     username='telecom_knowledge_publisher',
                     password=credentials['telecom_knowledge_publisher'], authSource='admin',
                     timeoutMS=15000, appname='telecom-schema-probe') as client:
        cases = [('document_versions', 'valid', version, True), ('chunks', 'valid', chunk, True)]
        for name, label, original, changes in [
            ('document_versions', 'missing-owner', version, {'information_owner': None}),
            ('document_versions', 'string-date', version, {'expires_at': '2030-01-01'}),
            ('document_versions', 'reversed-dates', version, {'expires_at': version['created_at']}),
            ('document_versions', 'empty-acl', version, {'acl': []}),
            ('chunks', 'wrong-dimensions', chunk, {'embedding': [0.1]*256}),
            ('chunks', 'wrong-profile', chunk, {'embedding_profile': 'unapproved'}),
            ('chunks', 'missing-tenant', chunk, {'tenant_id': None}),
            ('chunks', 'duplicate-pages', chunk, {'pages': [1, 1]}),
            ('chunks', 'boolean-page', chunk, {'pages': [True]}),
            ('chunks', 'oversized-text', chunk, {'text': 'x'*8001}),
        ]:
            cases.append((name, label, copy.deepcopy(original) | changes, False))
        for name, label, document, expected in cases:
            accepted = False
            with client.start_session() as session:
                session.start_transaction()
                try:
                    client.telecom_demo_knowledge[name].insert_one(document, session=session)
                    accepted = True
                except OperationFailure as error:
                    if error.code != 121:
                        raise
                finally:
                    session.abort_transaction()
            if accepted != expected:
                raise ValueError(f'Unexpected schema outcome: {name}/{label}')
            checks.append({'collection': name, 'case': label, 'accepted': accepted})
    with MongoClient('mongodb+srv://openai-sdk.qrmdk.mongodb.net/',
                     username='telecom_knowledge_reader',
                     password=credentials['telecom_knowledge_reader'], authSource='admin',
                     timeoutMS=15000, appname='telecom-native-search-probe') as client:
        reader = MongoKnowledgeReader(client.telecom_demo_knowledge)
        scope = Scope(version['tenant_id'], frozenset({'synthetic-reader'}), 'FiberBox', 'demo', '2.x')
        assert reader.search(hybrid_pipeline(scope, 'optical cable', [0.1]*1024, datetime.now(UTC))) == []
        assert reader.version(scope.tenant_id, version['_id']) is None
        assert reader.chunk(scope.tenant_id, version['_id'], 'c1', 1) is None
    evidence = {'checked_at': datetime.now(UTC).isoformat(), 'cluster': 'OpenAI-SDK',
                'validators': validators, 'schema_checks': checks,
                'native_rank_fusion': 'passed_empty_synthetic_scope',
                'rolled_back_writes': True, 'persisted_synthetic_documents': 0,
                'limitations': ['No corpus ranking or tenant/ACL acceptance claim',
                                'Other five collection validators remain pending',
                                'Native review and publication remain disabled']}
    Path('compatibility/phase4-storage-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS: 12 schema probes; native rank fusion on empty synthetic scope; no persisted fixtures')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Error messages may contain document/connection data; log only class/code.
        print(f'Storage verification stopped: {type(error).__name__}, code={getattr(error, "code", None)}')
        raise SystemExit(1) from None
