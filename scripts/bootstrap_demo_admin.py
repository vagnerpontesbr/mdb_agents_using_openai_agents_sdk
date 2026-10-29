"""Insert the selected demo administrator once; never reset an existing account."""
import argparse
import getpass
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compatibility.demo_auth.auth import Auth, UserExists
from compatibility.demo_auth.mongo import DATABASE, MongoUserStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-write", action="store_true")
    args = parser.parse_args()
    if not args.allow_write:
        print("Blocked: --allow-write is required")
        return 2
    uri, host = os.environ.get("APP_MONGODB_URI"), os.environ.get("APP_MONGODB_HOST")
    if not uri or not host or urlsplit(uri).scheme != "mongodb+srv" or urlsplit(uri).hostname != host:
        print("Blocked: inject the application-cluster URI and matching approved SRV host")
        return 2
    password = getpass.getpass("Initial administrator password: ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match")
        return 2
    from pymongo import MongoClient
    try:
        # One short installation operation, one client, default lazy pool.
        # Fail within 15 seconds rather than leaving bootstrap indefinitely waiting.
        with MongoClient(uri, appname="telecom-demo-bootstrap", timeoutMS=15_000) as client:
            Auth(MongoUserStore(client[DATABASE])).bootstrap(password)
        print("Initial administrator created; password stored only as a salted hash")
        return 0
    except UserExists:
        print("Administrator already exists; no credentials or roles changed")
        return 2
    except Exception as error:
        print(f"Bootstrap failed: {type(error).__name__}; details suppressed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
