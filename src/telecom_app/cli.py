"""Separate HTTP and one-off identity administration entrypoints."""

import argparse
import getpass

import uvicorn

from compatibility.demo_auth.auth import Auth, UserExists

from .config import Settings
from .database import connect, user_store


def serve() -> None:
    parser = argparse.ArgumentParser(description="Serve the loopback telecom demo")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    try:
        Settings.from_env()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    uvicorn.run("telecom_app.api:application", factory=True, host="127.0.0.1",
                port=args.port, workers=1,
                proxy_headers=False, access_log=False, timeout_keep_alive=5,
                limit_concurrency=16)


def admin() -> None:
    parser = argparse.ArgumentParser(description="One-off demo identity administration")
    parser.add_argument("operation", choices=("migrate", "bootstrap"))
    parser.add_argument("--apply", action="store_true", help="Permit identity database writes")
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply is required; no database operation performed")
    try:
        settings = Settings.from_env()
        with connect(settings) as client:
            store = user_store(client)
            if args.operation == "migrate":
                # Version 1: existing unique user ID and session/attempt expiry indexes.
                # Idempotent; no document rewrite, password reset or collection deletion.
                store.provision()
                print("Identity index migration v1 applied")
            else:
                password = getpass.getpass("Initial administrator password: ")
                if password != getpass.getpass("Repeat password: "):
                    raise ValueError("Passwords do not match")
                Auth(store).bootstrap(password)
                print("Initial administrator created")
    except UserExists:
        raise SystemExit("Administrator already exists; no account changed") from None
    except Exception:
        raise SystemExit("Administration failed; details suppressed") from None
