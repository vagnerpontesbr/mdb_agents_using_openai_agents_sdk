"""Real demo API/Engine controls; uses one synthetic requester account and native pending state."""
import argparse, getpass, http.cookiejar, json, os, secrets, sys, urllib.request, urllib.error, uuid
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
parser = argparse.ArgumentParser(description='Bounded native Engine requester-approval controls through the local demo API.')
parser.add_argument('--allow-live', action='store_true')
parser.add_argument('--url', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
base = args.url.rstrip('/')
if not __debug__ or not args.allow_live or urlsplit(base).scheme != 'http' or (urlsplit(base).hostname != '127.0.0.1') or urlsplit(base).username:
    parser.error('Requires --allow-live, loopback URL, and Python assertions enabled')
if urlsplit(os.environ['APP_MONGODB_URI']).hostname != os.environ['APP_MONGODB_HOST']:
    parser.error('Application database host mismatch')
password = getpass.getpass('Administrator password: ')
email = 'engine-' + uuid.uuid4().hex + '@example.test'
user_password = secrets.token_urlsafe(20)
created = None
report = {'checks': {}, 'status': 'failed', 'recorded_at': datetime.now(timezone.utc).isoformat()}

class NoRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, *args, **kwargs):
        return None

def client():
    return urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def call(c, path, data):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(), headers={'Origin': base, 'Content-Type': 'application/json'})
    try:
        r = c.open(req, timeout=140)
    except urllib.error.HTTPError as e:
        r = e
    return (r.code, json.loads(r.read()))
admin, user = (client(), client())
with MongoClient(os.environ['APP_MONGODB_URI'], timeoutMS=15000) as dbc:
    db = dbc.telecom_identity
    try:
        assert call(admin, '/api/login', {'email': 'admin@mongodb.com', 'password': password})[0] == 200
        status, created = call(admin, '/api/users', {'email': email, 'password': user_password, 'role': 'user'})
        assert status == 201
        assert call(user, '/api/login', {'email': email, 'password': user_password})[0] == 200
        status, pending = call(user, '/api/invoice', {})
        report['invocation_http_status'] = status
        if status != 200:
            report['invocation_result'] = pending
        assert status == 200
        report.update(execution_id=pending['execution_id'], session_id=pending['session_id'])
        assert pending['requester_id'] == created['user_id']
        report['checks']['engine_owner_matches_authenticated_app_user'] = True
        decision = {k: pending[k] for k in ['execution_id', 'action_digest']}
        decision['decision'] = 'approve'
        assert call(admin, '/api/pending', {'execution_id': pending['execution_id']})[0] == 403
        assert call(admin, '/api/review', decision)[0] == 403
        report['checks']['other_admin_denied_before_resume'] = True
        assert call(user, '/api/review', {**decision, 'requester_id': 'spoofed'})[0] == 400
        report['checks']['spoofed_identity_field_rejected'] = True
        assert call(user, '/api/review', {**decision, 'action_digest': 'stale'})[0] == 409
        report['checks']['changed_review_digest_rejected'] = True
        status, still = call(user, '/api/pending', {'execution_id': pending['execution_id']})
        assert status == 200 and still == pending
        report['checks']['native_pending_action_unchanged_after_denials'] = True
        status, result = call(user, '/api/review', decision)
        assert status == 200 and result['execution_id'] == pending['execution_id'] and (result['result']['invoice_id'] == 'demo-1')
        report['checks']['requester_approval_completed_original_execution'] = True
        assert call(user, '/api/review', decision)[0] == 409
        report['checks']['repeat_decision_rejected'] = True
        call(user, '/api/logout', {})
        call(admin, '/api/logout', {})
        report['status'] = 'passed'
    except Exception as error:
        report['error_class'] = type(error).__name__
    finally:
        if created and created.get('email') == email:
            db.sessions.delete_many({'user_id': created['user_id']})
            report['synthetic_user_removed'] = db.users.delete_one({'_id': email, 'user_id': created['user_id']}).deleted_count == 1
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['status'] == 'passed' and report.get('synthetic_user_removed') else 1)
