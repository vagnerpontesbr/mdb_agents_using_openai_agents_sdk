"""Opt-in live least-privilege check; synthetic records, sanitized evidence only."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit, urlunsplit
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compatibility.demo_auth.auth import AccessDenied, password_hash
from compatibility.demo_auth.mongo import MongoUserStore
from compatibility.demo_auth.sessions import SessionAuth

HOST = 'openai-sdk.qrmdk.mongodb.net'
MEMORY_HOST = 'clusterdemotelco.qrmdk.mongodb.net'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runtime_uri, cleanup_uri = os.environ.get('APP_MONGODB_URI', ''), os.environ.get('MONGODB_URI', '')
    if not args.allow_live or any(urlsplit(u).hostname != HOST or urlsplit(u).scheme != 'mongodb+srv'
                                  for u in (runtime_uri, cleanup_uri)):
        parser.error('Requires --allow-live and runtime/cleanup URIs for the approved application cluster')
    if urlsplit(runtime_uri).username == urlsplit(cleanup_uri).username:
        parser.error('Runtime and diagnostic cleanup identities must differ')
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure
    # One reused client per identity; sequential short CRUD probes, default lazy pools.
    # A 15-second operation deadline bounds each diagnostic request, not deployment capacity.
    runtime = MongoClient(runtime_uri, timeoutMS=15000, tz_aware=True)
    cleanup = MongoClient(cleanup_uri, timeoutMS=15000, tz_aware=True)
    tag = uuid.uuid4().hex
    emails = [f'permission-{tag}-{role}@example.invalid' for role in ('admin', 'user')]
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'checks': {},
              'scope': 'Real application collection privileges; independent of tenant/ACL authorization',
              'limitations': ['No capacity, public deployment or future application service permissions proof.']}
    db, admin_db = runtime.telecom_identity, cleanup.telecom_identity
    def denied(name, operation):
        try:
            operation()
        except OperationFailure as error:
            if error.code != 13:
                raise
            report['checks'][name] = True
        else:
            raise RuntimeError('Expected authorization denial')
    try:
        admin_db.users.insert_one({'_id': emails[0], 'user_id': tag, 'role': 'admin', 'active': True,
                                   'password_hash': password_hash(tag), 'schema_version': 1})
        store = MongoUserStore(db)
        store.provision()
        report['checks']['startup_indexes'] = True
        auth = SessionAuth(store)
        token, actor = auth.login(emails[0], tag, 'permission-' + tag)
        created = auth.register(token, email=emails[1], password=tag, role='user')
        assert created.role == 'user' and auth.principal(token).user_id == actor.user_id
        report['checks']['login_registration_session_read'] = True
        key = 'permission-' + tag
        expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
        assert store.consume_attempt(key, expiry) == 1 and store.consume_attempt(key, expiry) == 2
        report['checks']['attempt_insert_update'] = True
        auth.logout(token)
        try:
            auth.principal(token)
        except AccessDenied:
            report['checks']['logout_revokes_session'] = True
        else:
            raise RuntimeError('Session survived logout')
        denied('user_update_denied', lambda: db.users.update_one({'_id': emails[1]}, {'$set': {'role': 'admin'}}))
        denied('user_delete_denied', lambda: db.users.delete_one({'_id': 'absent-' + tag}))
        denied('other_collection_read_denied', lambda: db.unrelated.find_one({'_id': tag}))
        denied('other_collection_write_denied', lambda: db.unrelated.update_one({'_id': tag}, {'$set': {'probe': True}}))
        denied('other_database_read_denied', lambda: runtime.telecom_financial.invoices.find_one({'_id': tag}))
        denied('other_database_write_denied', lambda: runtime.telecom_financial.invoices.update_one({'_id': tag}, {'$set': {'probe': True}}))
        assert admin_db.users.find_one({'_id': emails[1]})['role'] == 'user'
        report['checks']['denied_update_preserved_user'] = True
        parsed = urlsplit(runtime_uri)
        userinfo = parsed.netloc.rsplit('@', 1)[0]
        other_uri = urlunsplit(parsed._replace(netloc=userinfo + '@' + MEMORY_HOST))
        with MongoClient(other_uri, timeoutMS=15000) as other:
            try:
                other.telecom_identity.users.find_one({'_id': tag})
            except OperationFailure as error:
                if error.code not in (13, 18):
                    raise
                report['checks']['memory_cluster_access_denied'] = True
                report['memory_cluster_denial_code'] = error.code
            else:
                raise RuntimeError('Unexpected memory cluster access')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed_or_incomplete', error_class=type(error).__name__,
                      error_code=getattr(error, 'code', None))
    finally:
        try:
            admin_db.sessions.delete_many({'email': {'$in': emails}})
            admin_db.users.delete_many({'_id': {'$in': emails}})
            admin_db.login_attempts.delete_one({'_id': 'permission-' + tag})
            # The login throttle entry expires natively at its minute boundary.
            report['synthetic_accounts_removed'] = admin_db.users.count_documents({'_id': {'$in': emails}}) == 0
        except Exception as error:
            report.update(status='failed_or_incomplete', cleanup_error_class=type(error).__name__)
        runtime.close()
        cleanup.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report.get('status') == 'passed' and report.get('synthetic_accounts_removed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
