"""Verify approved Phase 5 roles, validators and readiness using aborted writes."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure


def fixture(kind, marker):
    now = datetime.now(UTC)
    if kind == 'retrieval_cache':
        return dict(_id=marker,tenant_id='phase5-transaction-probe',scope_key='probe',
            policy_version='demo-v1',embedding_profile='voyage-context-4:1024:v1',
            query_sha256='a'*64,embedding=[.01]*1024,created_at=now,
            expires_at=now+timedelta(minutes=1),sources=[dict(version_key='probe',chunk_id='0',
                revision=1,text_sha256='b'*64)])
    return dict(_id=marker,dataset_id='phase5-transaction-probe',tenant_id='synthetic-probe',
        version_key=marker,chunk_id='0',source_checksum='a'*64,
        embedding_profile='voyage-context-4:comparison-v1',eligible=True,
        text='Synthetic schema probe.',embedding_256=[.01]*256,embedding_1024=[.01]*1024)


def main():
    plan=json.loads(Path('compatibility/phase5-resource-proposal.json').read_text())
    credentials=dict(line.split('=',1) for line in Path('.env.phase5').read_text().splitlines())
    namespaces=[(c['database'],c['name']) for c in plan['collections']]
    namespaces += [('telecom_identity','users'),('telecom_demo_knowledge','document_versions'),
                   ('telecom_demo_knowledge','owners'),('telecom_demo_ingestion','jobs'),
                   ('telecom_eval_knowledge','phase0_search_probe')]
    checks=[]
    for identity in plan['runtime_identities']:
        allowed={(p['database'],p['collection']) for p in identity['privileges']}
        with MongoClient('mongodb+srv://openai-sdk.qrmdk.mongodb.net/',
                         username=identity['username'],password=credentials[identity['username']],
                         authSource='admin',maxPoolSize=1,minPoolSize=0,timeoutMS=15000,
                         appname='telecom-phase5-role-probe') as client:
            for db,coll in namespaces:
                for action in ('find','insert','update','remove'):
                    marker='phase5-'+uuid4().hex
                    with client.start_session() as session:
                        session.start_transaction()
                        permitted=False
                        try:
                            target=client[db][coll]
                            if action=='find': target.find_one({'_id':marker},session=session)
                            elif action=='insert': target.insert_one(fixture(coll,marker),session=session)
                            elif action=='update': target.update_one({'_id':marker},
                                {'$set':{'tenant_id':'synthetic-probe'}},session=session)
                            else: target.delete_one({'_id':marker},session=session)
                            permitted=True
                        except OperationFailure as error:
                            if error.code!=13: raise
                        finally: session.abort_transaction()
                    assert permitted == ((db,coll) in allowed)
                    checks.append(dict(user=identity['username'],namespace=f'{db}.{coll}',
                                       action=action,allowed=permitted))
            for db,coll in allowed:
                with client.start_session() as session:
                    session.start_transaction()
                    try:
                        client[db][coll].insert_one({'_id':'phase5-'+uuid4().hex},session=session)
                        raise AssertionError('Malformed row accepted')
                    except OperationFailure as error:
                        assert error.code==121
                    finally: session.abort_transaction()
    with MongoClient(os.environ['MONGODB_URI'],maxPoolSize=1,minPoolSize=0,timeoutMS=15000) as client:
        indexes=[]
        for c in plan['collections']:
            info=list(client[c['database']].list_collections(filter={'name':c['name']}))[0]
            assert all(info['options'][key]==c[key]
                       for key in ('validator','validationAction','validationLevel'))
            indexes.extend({k:i.get(k) for k in ('name','status','queryable')}
                           for i in client[c['database']][c['name']].list_search_indexes())
    path=Path('compatibility/phase5-resource-evidence.json')
    evidence=json.loads(path.read_text())
    evidence.update(role_schema_checked_at=datetime.now(UTC).isoformat(),role_probes=checks,
        valid_insert_probes=2,malformed_insert_denials=2,search_indexes=indexes)
    evidence['pending']=[p for p in evidence['pending'] if p!='live_role_schema_probes']
    path.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'role_checks':len(checks),'schema_checks':4,'search_indexes':indexes}))


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'error_type':type(error).__name__,'details_suppressed':True}))
        raise SystemExit(1) from None
