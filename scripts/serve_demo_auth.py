"""Loopback-only demo login and administrator registration compatibility UI."""
import argparse
from dataclasses import asdict
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compatibility.demo_auth.auth import AccessDenied, UserExists
from compatibility.demo_auth.mongo import DATABASE, MongoUserStore
from compatibility.demo_auth.sessions import RateLimited, SESSION_SECONDS, SessionAuth
from compatibility.demo_auth.engine import EngineReview, EngineTransport, ReviewConflict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--engine-review", action="store_true",
                        help="Enable the bounded synthetic Engine invoice/review flow")
    args = parser.parse_args()
    uri, host = os.environ.get("APP_MONGODB_URI"), os.environ.get("APP_MONGODB_HOST")
    if not uri or not host or urlsplit(uri).scheme != "mongodb+srv" or urlsplit(uri).hostname != host:
        parser.error("Inject APP_MONGODB_URI and matching approved APP_MONGODB_HOST")
    from pymongo import MongoClient
    # Single long-lived client shared by at most eight concurrent short handlers.
    client = MongoClient(uri, appname="telecom-demo-auth", timeoutMS=15_000, tz_aware=True)
    store = MongoUserStore(client[DATABASE])
    store.provision()
    auth = SessionAuth(store)
    engine = EngineReview(auth, EngineTransport()) if args.engine_review else None
    origin = f"http://127.0.0.1:{args.port}"
    slots = threading.BoundedSemaphore(8)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, data, cookie=None, html=False):
            body = data.encode() if html else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'")
            if cookie is not None:
                # HTTP is intentionally restricted to loopback. A deployed HTTPS app
                # must additionally set Secure; never expose this demo server publicly.
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(body)

        def token(self):
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            return cookie["demo_session"].value if "demo_session" in cookie else ""

        def handle_route(self, post=False):
            if self.headers.get("Host") != origin.removeprefix("http://"):
                return self.respond(403, {"error": "Invalid host"})
            if post and (self.headers.get("Origin") != origin
                         or self.headers.get_content_type() != "application/json"):
                return self.respond(403, {"error": "Invalid origin or content type"})
            if not slots.acquire(blocking=False):
                return self.respond(503, {"error": "Server busy"})
            try:
                self.connection.settimeout(10)
                data = {}
                if post:
                    size = int(self.headers.get("Content-Length", "-1"))
                    if not 0 < size <= 4096 or self.headers.get("Transfer-Encoding"):
                        raise ValueError("Invalid request size")
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError("Incomplete request")
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise ValueError("Expected an object")
                if self.path == "/" and not post:
                    html = Path(__file__).with_name("demo_auth.html").read_text()
                    return self.respond(200, html.replace("__ENGINE_ENABLED__", json.dumps(bool(engine))), html=True)
                if self.path == "/api/me" and not post:
                    return self.respond(200, asdict(auth.principal(self.token())))
                if self.path == "/api/login" and post:
                    if set(data) != {"email", "password"}:
                        raise ValueError("Expected email and password")
                    token, principal = auth.login(data["email"], data["password"], self.client_address[0])
                    # Re-login invalidates the browser's previous session when present.
                    if self.token():
                        try:
                            auth.logout(self.token())
                        except AccessDenied:
                            pass
                    return self.respond(200, asdict(principal),
                        f"demo_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}")
                if self.path == "/api/logout" and post:
                    auth.logout(self.token())
                    return self.respond(200, {"status": "logged_out"},
                        "demo_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
                if self.path == "/api/users" and post:
                    if set(data) - {"email", "password", "role"} or not {"email", "password"} <= set(data):
                        raise ValueError("Expected email, password and optional role")
                    return self.respond(201, asdict(auth.register(self.token(), **data)))
                if self.path == "/api/invoice" and post and engine:
                    if data:
                        raise ValueError("No caller-selected user or session accepted")
                    return self.respond(200, engine.create(self.token()))
                if self.path == "/api/pending" and post and engine:
                    if set(data) != {"execution_id"}:
                        raise ValueError("Expected execution ID")
                    return self.respond(200, engine.pending(self.token(), data["execution_id"]))
                if self.path == "/api/review" and post and engine:
                    if set(data) != {"execution_id", "action_digest", "decision"}:
                        raise ValueError("Unexpected review fields")
                    return self.respond(200, engine.decide(self.token(), **data))
                self.respond(404, {"error": "Not found"})
            except AccessDenied as error:
                self.respond(403 if str(error) in ("Administrator required", "Only the original requester may approve") else 401,
                             {"error": str(error)})
            except ReviewConflict:
                self.respond(409, {"error": "Review conflict; reload the pending action"})
            except UserExists:
                self.respond(409, {"error": "Email already registered"})
            except RateLimited:
                self.respond(429, {"error": "Too many login attempts; try again next minute"})
            except (ValueError, TypeError, TimeoutError):
                self.respond(400, {"error": "Invalid request"})
            except Exception:
                self.respond(503, {"error": "Operation unavailable; outcome may be uncertain"})
            finally:
                slots.release()

        def do_GET(self):
            self.handle_route()

        def do_POST(self):
            self.handle_route(post=True)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    print(f"Demo authentication: {origin}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":
    main()
