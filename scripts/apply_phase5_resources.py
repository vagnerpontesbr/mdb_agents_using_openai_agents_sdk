"""Apply only the approved Phase 5 proposal, with complete preflight drift checks."""

import argparse
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

from apply_knowledge_resources import atlas, normalized_actions
from prepare_phase5_resources import proposal


def actions(identity):
    return [{'action': action, 'resources': [
        {'db': p['database'], 'collection': p['collection']} for p in identity['privileges']
        if action in p['actions']]} for action in sorted({
            action for p in identity['privileges'] for action in p['actions']})]


def check_classic(existing, index):
    return (existing['key'] == list(index['key'].items())
            and bool(existing.get('unique')) == bool(index.get('unique'))
            and existing.get('expireAfterSeconds') == index.get('expireAfterSeconds')
            and not existing.get('partialFilterExpression') and not existing.get('sparse'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-approved', action='store_true', required=True)
    parser.parse_args()
    source = Path('compatibility/phase5-resource-proposal.json').read_bytes()
    plan = json.loads(source)
    if plan != proposal():
        raise RuntimeError('Proposal differs from the reviewed definitions')
    uri = os.environ['MONGODB_URI']
    if urlsplit(uri).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise RuntimeError('Unexpected provisioning cluster')
    credential_file = Path('.env.phase5')
    if credential_file.is_symlink():
        raise RuntimeError('Credential path cannot be a symlink')
    credentials = {}
    if credential_file.exists():
        if credential_file.stat().st_mode & 0o077:
            raise RuntimeError('Credential file must be private')
        credentials = dict(line.split('=', 1) for line in credential_file.read_text().splitlines())
    project = plan['project_id']
    roles = {r['roleName']: r for r in atlas('customDatabaseRoles','listCustomDbRoles',project)}
    inventory = atlas('databaseUsers','listDatabaseUsers',project)
    if inventory.get('totalCount', len(inventory['results'])) > len(inventory['results']):
        raise RuntimeError('User inventory requires pagination')
    users = {r['username']: r for r in inventory['results']}
    for identity in plan['runtime_identities']:
        role, user = roles.get(identity['role']), users.get(identity['username'])
        if role and (role.get('inheritedRoles') or
                     normalized_actions(role['actions']) != normalized_actions(actions(identity))):
            raise RuntimeError('Existing role differs from approved privileges')
        if user and (user.get('roles') != [{'roleName':identity['role'],'databaseName':'admin'}]
                     or user.get('scopes') != [identity['scope']]
                     or user.get('databaseName') != 'admin'
                     or identity['username'] not in credentials):
            raise RuntimeError('Existing user differs or private credential unavailable')
    # A single sequential administrative workload; no concurrent admission or warm pool needed.
    with MongoClient(uri, maxPoolSize=1, minPoolSize=0, timeoutMS=15000,
                     appname='telecom-phase5-provision') as client:
        existing_collections = {}
        for c in plan['collections']:
            info = list(client[c['database']].list_collections(filter={'name':c['name']}))
            existing_collections[c['database'],c['name']] = bool(info)
            if info and any(info[0]['options'].get(field) != c[field]
                            for field in ('validator','validationLevel','validationAction')):
                raise RuntimeError('Existing collection validator differs')
        classic, search = {}, {}
        for index in plan['classic_indexes']:
            coll = client[index['database']][index['collection']]
            existing = coll.index_information().get(index['name']) if existing_collections[
                index['database'],index['collection']] else None
            classic[index['name']] = existing
            if existing and not check_classic(existing,index):
                raise RuntimeError('Existing classic index differs')
        for index in plan['search_indexes']:
            coll = client[index['database']][index['collection']]
            existing = list(coll.list_search_indexes(index['name'])) if existing_collections[
                index['database'],index['collection']] else []
            search[index['name']] = existing
            if existing and (existing[0]['latestDefinition'] != index['definition']
                             or existing[0]['type'] != index['type']):
                raise RuntimeError('Existing search index differs')
        # All preflight checks precede the first mutation. Application remains incremental.
        for c in plan['collections']:
            if not existing_collections[c['database'],c['name']]:
                client[c['database']].create_collection(c['name'], **{
                    field:c[field] for field in ('validator','validationLevel','validationAction')})
        for index in plan['classic_indexes']:
            if not classic[index['name']]:
                client[index['database']][index['collection']].create_index(
                    list(index['key'].items()), name=index['name'], **{
                        k:index[k] for k in ('unique','expireAfterSeconds') if k in index})
        for index in plan['search_indexes']:
            if not search[index['name']]:
                client[index['database']][index['collection']].create_search_index(SearchIndexModel(
                    definition=index['definition'],name=index['name'],type=index['type']))
        for identity in plan['runtime_identities']:
            if identity['role'] not in roles:
                atlas('customDatabaseRoles','createCustomDbRole',project,{
                    'roleName':identity['role'],'inheritedRoles':[],'actions':actions(identity)})
            name = identity['username']
            if name not in users:
                if name not in credentials:
                    credentials[name] = secrets.token_urlsafe(36)
                    fd = os.open(credential_file,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                    with os.fdopen(fd,'w') as output:
                        output.write(''.join(f'{key}={value}\n' for key,value in credentials.items()))
                        output.flush()
                        os.fsync(output.fileno())
                atlas('databaseUsers','createDatabaseUser',project,{
                    'databaseName':'admin','username':name,'password':credentials[name],
                    'roles':[{'roleName':identity['role'],'databaseName':'admin'}],
                    'scopes':[identity['scope']]})
        readiness = []
        for index in plan['search_indexes']:
            item = list(client[index['database']][index['collection']].list_search_indexes(index['name']))[0]
            readiness.append({k:item.get(k) for k in ('name','status','queryable')})
    evidence = {'checked_at':datetime.now(UTC).isoformat(),
        'proposal_sha256':hashlib.sha256(source).hexdigest(),
        'status':'resources_applied_not_enabled','collections':len(plan['collections']),
        'strict_validators':2,'classic_indexes':3,'search_indexes':readiness,
        'runtime_identities':[i['username'] for i in plan['runtime_identities']],
        'pending':['live_role_schema_probes','cache_domain_acceptance','workspace_secret_binding',
                   'evaluation_corpus','hosted_integration']}
    Path('compatibility/phase5-resource-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status':'provisioning_stopped','error_type':type(error).__name__,
                          'details_suppressed':True,'partial_application_possible':True}))
        raise SystemExit(1) from None
