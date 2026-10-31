"""Provision the explicitly approved initial demo owner; never grant runtime owner writes."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pymongo import MongoClient


def main():
    uri = os.environ['MONGODB_URI']
    if urlsplit(uri).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise ValueError('Unexpected cluster')
    with MongoClient(uri, timeoutMS=15000, appname='telecom-owner-provision') as client:
        user = client.telecom_identity.users.find_one(
            {'_id': 'admin@mongodb.com', 'role': 'admin'}, {'user_id': 1})
        if not user or not user.get('user_id'):
            raise ValueError('Approved initial administrator is unavailable')
        owner = {'_id': 'synthetic-telecom:demo-document-owner', 'tenant_id': 'synthetic-telecom',
                 'owner_id': 'demo-document-owner', 'active': True, 'user_ids': [user['user_id']]}
        collection = client.telecom_demo_knowledge.owners
        existing = collection.find_one({'_id': owner['_id']})
        if existing is not None and existing != owner:
            raise ValueError('Owner registry drift; refusing to overwrite')
        collection.update_one({'_id': owner['_id']}, {'$setOnInsert': owner}, upsert=True)
        assert collection.find_one({'_id': owner['_id']}) == owner
    evidence = {'checked_at': datetime.now(UTC).isoformat(), 'owner_id': owner['owner_id'],
                'tenant_id': owner['tenant_id'], 'initial_admin_owner_registered': True,
                'runtime_owner_write_permissions_changed': False}
    Path('compatibility/phase4-owner-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Owner provisioning stopped: {type(error).__name__}; details suppressed')
        raise SystemExit(1) from None
