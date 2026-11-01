"""Apply only the reviewed additive language validators; requires explicit approval."""

import argparse
import json
import os
from pathlib import Path

from telecom_app.config import Settings
from telecom_app.database import connect
from telecom_app.knowledge_schema import knowledge_validators


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--apply-approved-change', action='store_true', required=True)
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text())
    expected = knowledge_validators()
    entries = proposal['commands']
    if (proposal.get('host') != 'openai-sdk.qrmdk.mongodb.net'
            or len(entries) != 2
            or {row['collection'] for row in entries} != {'document_versions', 'chunks'}):
        raise ValueError('Unexpected proposal scope')
    for row in entries:
        name = row['collection']
        allowed = {'collMod': name, 'validator': expected[name],
                   'validationLevel': 'strict', 'validationAction': 'error'}
        if row['database'] != 'telecom_demo_knowledge' or row['command'] != allowed:
            raise ValueError('Proposal differs from validated source')
    with connect(Settings(os.environ['MONGODB_URI'])) as client:
        db = client.telecom_demo_knowledge
        for row in entries:
            current = db[row['collection']].options()
            if (current.get('validator') not in (row['expected_before'], row['command']['validator'])
                    or current.get('validationLevel') != 'strict'
                    or current.get('validationAction') != 'error'):
                raise ValueError('Live validator drift; no changes applied')
            if db[row['collection']].count_documents(
                    {'$nor': [row['command']['validator']]}, maxTimeMS=15000):
                raise ValueError('Existing documents require separate migration')
        for row in entries:
            db.command(row['command'])
            if db[row['collection']].options().get('validator') != row['command']['validator']:
                raise ValueError('Validator verification failed; inspect partial application')
            print(json.dumps({'collection': row['collection'], 'validator_verified': True}))
    print('Only two validators applied; no document/index/role or Engine configuration changed')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Schema application stopped: ' + type(error).__name__)
        raise SystemExit(1) from None
