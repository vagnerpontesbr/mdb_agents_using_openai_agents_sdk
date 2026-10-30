"""Live Phase 4 role probes; synthetic writes are rolled back in transactions."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure


def main():
    plan = json.loads(Path('compatibility/phase4-resource-plan.json').read_text())
    credentials = dict(line.split('=', 1) for line in
                       Path('.env.phase4').read_text().splitlines() if line)
    evidence = json.loads(Path('compatibility/phase4-resource-evidence.json').read_text())
    checks = []
    for user in plan['runtime_users']:
        # Sequential demo probes, one reused client per identity, bounded operations.
        with MongoClient('mongodb+srv://openai-sdk.qrmdk.mongodb.net/',
                         username=user['username'], password=credentials[user['username']],
                         authSource='admin', timeoutMS=15000,
                         appname='telecom-phase4-role-probe') as client:
            allowed = {(p['resource']['db'], p['resource']['collection']): p['actions']
                       for p in plan['runtime_roles'][user['role']]}
            resources = [(db, coll) for db, names in plan['collections'].items() for coll in names]
            resources.append(('telecom_identity', 'users'))
            for db, coll in resources:
                for action in ('find', 'insert', 'update', 'remove'):
                    expected = action in allowed.get((db, coll), [])
                    marker = 'phase4-role-probe-' + uuid4().hex
                    outcome = False
                    schema_rejected = False
                    with client.start_session() as session:
                        session.start_transaction()
                        try:
                            collection = client[db][coll]
                            if action == 'find':
                                collection.find_one({'_id': marker}, session=session)
                            elif action == 'insert':
                                collection.insert_one({'_id': marker, 'tenant_id': 'synthetic-probe'},
                                                      session=session)
                            elif action == 'update':
                                collection.update_one({'_id': marker}, {'$set': {'probe': True}},
                                                      session=session)
                            else:
                                collection.delete_one({'_id': marker}, session=session)
                            outcome = True
                        except OperationFailure as error:
                            # A schema rejection establishes authorization but not a
                            # successful insert. Valid writes are tested separately.
                            if error.code == 121 and action in ('insert', 'update'):
                                outcome = True
                                schema_rejected = True
                            elif error.code != 13:
                                raise
                        finally:
                            session.abort_transaction()
                    if outcome != expected:
                        raise RuntimeError(f'Unexpected permission: {user["username"]} {db}.{coll} {action}')
                    checks.append({'user': user['username'], 'namespace': f'{db}.{coll}',
                                   'action': action, 'result': (
                                       'authorized_schema_rejected' if schema_rejected else
                                       'allowed' if outcome else 'denied')})
    with MongoClient(os.environ['MONGODB_URI'], timeoutMS=15000,
                     appname='telecom-phase4-readiness') as client:
        evidence['search_indexes'] = [{key: index.get(key) for key in
                                      ('name', 'type', 'status', 'queryable')}
                                     for index in client.telecom_demo_knowledge.chunks.list_search_indexes()]
    evidence['role_probes'] = checks
    evidence['role_probes_checked_at'] = datetime.now(UTC).isoformat()
    evidence['pending'] = [item for item in evidence['pending'] if item != 'live_role_probes']
    Path('compatibility/phase4-resource-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'role_probes_passed': len(checks), 'search_indexes': evidence['search_indexes']}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Resource verification stopped: {type(error).__name__}; no credentials printed')
        raise SystemExit(1) from None
