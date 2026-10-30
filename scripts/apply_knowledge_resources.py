"""Apply the explicitly approved Phase 4 plan; refuse existing resource drift.

Credentials are saved only in an ignored, mode-0600 file. This does not enable
publication: schema validation and native review remain separate acceptance gates.
"""

import argparse
import json
import os
import secrets
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pymongo import MongoClient
from pymongo.operations import SearchIndexModel


def atlas(group, operation, project, payload=None):
    result = subprocess.run(
        ['atlas', 'api', group, operation, '--groupId', project,
         '--version', '2023-01-01'],
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        # CLI diagnostics may contain connection details; never echo them.
        raise RuntimeError(f'Atlas {operation} failed (exit {result.returncode})')
    return json.loads(result.stdout)


def role_actions(privileges):
    actions = {}
    for privilege in privileges:
        for action in privilege['actions']:
            actions.setdefault(action.upper(), []).append(privilege['resource'])
    return [{'action': action, 'resources': resources} for action, resources in actions.items()]


def normalized_actions(actions):
    return sorted((item['action'], resource['db'], resource['collection'])
                  for item in actions for resource in item['resources'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-approved', action='store_true', required=True)
    args = parser.parse_args()
    assert args.apply_approved
    plan = json.loads(Path('compatibility/phase4-resource-plan.json').read_text())
    uri = os.environ['MONGODB_URI']
    if urlsplit(uri).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise RuntimeError('Refusing an unexpected cluster')
    project = plan['project_id']
    roles = {r['roleName']: r for r in atlas(
        'customDatabaseRoles', 'listCustomDbRoles', project)}
    # Refuse incomplete pagination rather than missing an existing identity.
    response = atlas('databaseUsers', 'listDatabaseUsers', project)
    if response.get('totalCount', len(response['results'])) > len(response['results']):
        raise RuntimeError('Database user inventory requires pagination')
    users = {u['username']: u for u in response['results']}
    credentials_path = Path('.env.phase4')
    credentials = {}
    if credentials_path.exists():
        if credentials_path.stat().st_mode & 0o077:
            raise RuntimeError('Credential file permissions must be 0600')
        credentials = dict(line.split('=', 1) for line in
                           credentials_path.read_text().splitlines() if line)
    # Preflight role/user drift before any mutation.
    for name, privileges in plan['runtime_roles'].items():
        if name in roles and (roles[name].get('inheritedRoles') or
                normalized_actions(roles[name]['actions']) !=
                normalized_actions(role_actions(privileges))):
            raise RuntimeError(f'Role drift: {name}')
    for user in plan['runtime_users']:
        name = user['username']
        if name in users:
            existing = users[name]
            if (existing['roles'] != [{'roleName': user['role'], 'databaseName': 'admin'}]
                    or existing.get('scopes') != [{'name': plan['cluster'], 'type': 'CLUSTER'}]
                    or existing.get('databaseName') != 'admin'
                    or name not in credentials):
                raise RuntimeError(f'User drift or unavailable private credential: {name}')
    # One sequential provisioning client; 15 seconds bounds each operation.
    with MongoClient(uri, timeoutMS=15000, appname='telecom-phase4-provision') as client:
        client.admin.command('ping')
        for db, names in plan['collections'].items():
            existing = client[db].list_collection_names()
            for name in names:
                if name not in existing:
                    client[db].create_collection(name)
        for index in plan['classic_indexes']:
            collection = client[index['database']][index['collection']]
            existing = collection.index_information().get(index['name'])
            keys = list(index['key'].items())
            if existing:
                if (existing['key'] != keys or bool(existing.get('unique')) !=
                        bool(index.get('unique'))):
                    raise RuntimeError(f'Index drift: {index["name"]}')
            else:
                collection.create_index(keys, name=index['name'],
                                        unique=index.get('unique', False))
        for index in plan['search_indexes']:
            collection = client[index['database']][index['collection']]
            existing = list(collection.list_search_indexes(index['name']))
            if existing:
                if (existing[0]['latestDefinition'] != index['definition']
                        or existing[0]['type'] != index['type']):
                    raise RuntimeError(f'Search index drift: {index["name"]}')
            else:
                collection.create_search_index(SearchIndexModel(
                    definition=index['definition'], name=index['name'], type=index['type']))
        for name, privileges in plan['runtime_roles'].items():
            if name not in roles:
                atlas('customDatabaseRoles', 'createCustomDbRole', project,
                      {'roleName': name, 'actions': role_actions(privileges),
                       'inheritedRoles': []})
        for user in plan['runtime_users']:
            name = user['username']
            if name not in users:
                if name not in credentials:
                    credentials[name] = secrets.token_urlsafe(36)
                    # Persist before the remote call so an interrupted response is recoverable.
                    fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, 'w') as output:
                        output.write(''.join(f'{key}={value}\n' for key, value in credentials.items()))
                atlas('databaseUsers', 'createDatabaseUser', project, {
                    'databaseName': 'admin', 'username': name, 'password': credentials[name],
                    'roles': [{'roleName': user['role'], 'databaseName': 'admin'}],
                    'scopes': [{'name': plan['cluster'], 'type': 'CLUSTER'}],
                })
        evidence = {
            'checked_at': datetime.now(UTC).isoformat(), 'cluster': plan['cluster'],
            'status': 'resources_applied_not_enabled',
            'collections': plan['collections'],
            'classic_indexes': plan['classic_indexes'],
            'search_indexes': [{key: index.get(key) for key in
                                ('name', 'type', 'status', 'queryable')}
                               for index in client.telecom_demo_knowledge.chunks.list_search_indexes()],
            'roles': list(plan['runtime_roles']),
            'users': [user['username'] for user in plan['runtime_users']],
            'pending': ['schema_validation', 'live_role_probes', 'native_review_integration',
                        'application_integration'],
        }
        Path('compatibility/phase4-resource-evidence.json').write_text(
            json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Provisioning stopped: {type(error).__name__}; no credentials printed')
        raise SystemExit(1) from None
