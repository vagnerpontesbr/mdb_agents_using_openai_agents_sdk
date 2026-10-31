"""Apply remaining approved-domain validators only when existing data already conforms."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pymongo import MongoClient
from pymongo.errors import OperationFailure

from telecom_app.curation_schema import remaining_validators


def main():
    uri = os.environ['MONGODB_URI']
    if urlsplit(uri).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise ValueError('Unexpected application cluster')
    validators = remaining_validators()
    with MongoClient(uri, timeoutMS=15000, appname='telecom-curation-schema') as client:
        for namespace, validator in validators.items():
            database, name = namespace.split('.')
            collection = client[database][name]
            current = collection.options().get('validator')
            if current not in (None, {}, validator):
                raise ValueError('Existing validator drift')
            if collection.find_one({'$nor': [validator]}, {'_id': 1}):
                raise ValueError('Existing documents require a separate migration')
        checks = []
        for namespace, validator in validators.items():
            database, name = namespace.split('.')
            client[database].command('collMod', name, validator=validator,
                                     validationLevel='strict', validationAction='error')
            options = client[database][name].options()
            assert options['validator'] == validator
            with client.start_session() as session:
                session.start_transaction()
                try:
                    client[database][name].insert_one({'_id': 'synthetic-invalid-schema'}, session=session)
                    raise AssertionError('Invalid shape accepted')
                except OperationFailure as error:
                    if error.code != 121:
                        raise
                finally:
                    session.abort_transaction()
            checks.append(namespace)
    evidence = {'checked_at': datetime.now(UTC).isoformat(), 'validators': validators,
                'invalid_shape_rejections_passed': checks, 'existing_data_conformed': True,
                'limitations': ['Nested staging result provenance is additionally enforced in Python',
                                'Schema validation is not native publication approval']}
    Path('compatibility/phase4-curation-schema-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('PASS: five strict/error validators applied; five malformed inserts rejected')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Curation schema check stopped: {type(error).__name__}, code={getattr(error, "code", None)}')
        raise SystemExit(1) from None
