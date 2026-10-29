"""Real localhost/Atlas controls; prompts for admin password, removes only its synthetic user."""
import argparse, getpass, http.cookiejar, json, secrets, sys, os, urllib.request, urllib.error, uuid
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compatibility.demo_auth.mongo import DATABASE
parser = argparse.ArgumentParser(description='Opt-in localhost/Atlas authentication controls using a disposable synthetic user.')
parser.add_argument('--allow-live', action='store_true')
parser.add_argument('--url', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
base = args.url.rstrip('/')
if not args.allow_live or urlsplit(base).scheme != 'http' or urlsplit(base).hostname != '127.0.0.1' or urlsplit(base).username:
    parser.error('Requires --allow-live and an HTTP loopback URL')
if not __debug__:
    parser.error('Run without Python optimization; this diagnostic requires assertions')
password = getpass.getpass('Administrator password: ')
email = 'phase0-' + uuid.uuid4().hex + '@example.test'
user_password = secrets.token_urlsafe(20)
created = None
report = {'checks': {}, 'status': 'failed', 'recorded_at': datetime.now(timezone.utc).isoformat()}

class NoRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, *args, **kwargs):
        return None

def client():
    return urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def call(c, path, data=None, origin=None):
    headers = {'Origin': origin or base, 'Content-Type': 'application/json'}
    req = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
    try:
        r = c.open(req, timeout=20)
    except urllib.error.HTTPError as e:
        r = e
    return (r.code, json.loads(r.read()), r.headers)
admin, user, anon = (client(), client(), client())
uri = os.environ['APP_MONGODB_URI']
if urlsplit(uri).hostname != os.environ['APP_MONGODB_HOST']:
    parser.error('Application database host mismatch')
with MongoClient(uri, timeoutMS=15000) as dbclient:
    db = dbclient[DATABASE]
    try:
        assert call(anon, '/api/me')[0] == 401
        report['checks']['anonymous_rejected'] = True
        assert call(admin, '/api/login', {'email': 'admin@mongodb.com', 'password': password}, 'https://untrusted.example')[0] == 403
        report['checks']['foreign_origin_rejected'] = True
        status, principal, headers = call(admin, '/api/login', {'email': 'admin@mongodb.com', 'password': password})
        assert status == 200 and principal['role'] == 'admin' and ('password_hash' not in principal)
        cookie = headers.get('Set-Cookie', '')
        assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
        report['checks']['admin_login_cookie'] = True
        status, created, _ = call(admin, '/api/users', {'email': email, 'password': user_password, 'role': 'user'})
        assert status == 201 and created['role'] == 'user'
        report['checks']['admin_registration'] = True
        assert call(admin, '/api/users', {'email': email.upper(), 'password': user_password, 'role': 'admin'})[0] == 409
        report['checks']['duplicate_does_not_promote'] = True
        assert call(user, '/api/login', {'email': email, 'password': user_password})[0] == 200
        assert call(user, '/api/users', {'email': 'denied-' + email, 'password': user_password, 'role': 'admin'})[0] == 403
        report['checks']['user_cannot_register_or_escalate'] = True
        record = db.users.find_one({'_id': email})
        assert record['role'] == 'user' and record['password_hash'] != user_password
        assert 'password' not in record
        report['checks']['atlas_persistence_hashed'] = True
        assert call(user, '/api/logout', {})[0] == 200 and call(user, '/api/me')[0] == 401
        assert call(admin, '/api/logout', {})[0] == 200 and call(admin, '/api/me')[0] == 401
        report['checks']['logout_revoked'] = True
        for _ in range(10):
            status, _, _ = call(anon, '/api/login', {'email': 'missing@example.test', 'password': user_password})
            if status == 429:
                break
            assert status == 401
        assert status == 429
        report['checks']['login_rate_limited'] = True
        initial = db.users.find_one({'_id': 'admin@mongodb.com'})
        assert initial['role'] == 'admin' and initial['active'] is True and ('password' not in initial)
        report['checks']['bootstrap_admin_present'] = True
        report['status'] = 'passed'
    except Exception as error:
        report['error_class'] = type(error).__name__
    finally:
        if created and created.get('email') == email:
            db.sessions.delete_many({'user_id': created['user_id']})
            deleted = db.users.delete_one({'_id': email, 'user_id': created['user_id']})
            report['synthetic_user_removed'] = deleted.deleted_count == 1
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['status'] == 'passed' and report.get('synthetic_user_removed') else 1)
