"""One bounded client per process; no access to Engine-managed namespaces."""

from typing import Any

from pymongo import MongoClient

from compatibility.demo_auth.mongo import MongoUserStore

from .config import CONCURRENCY, DATABASE, Settings


def connect(settings: Settings) -> MongoClient[dict[str, Any]]:
    # Local demo: at most eight admitted HTTP requests, short identity operations.
    # Sixteen slots leave headroom; no prewarming for intermittent demo traffic.
    # Each operation has a 15s budget; wait at most 2s for pool contention.
    return MongoClient(
        settings.mongodb_uri, appname="telecom-foundation", tz_aware=True,
        maxPoolSize=CONCURRENCY * 2, minPoolSize=0, timeoutMS=15_000,
        waitQueueTimeoutMS=2_000,
    )


def user_store(client: MongoClient[dict[str, Any]]) -> Any:
    return MongoUserStore(client[DATABASE])


def verify_connection(client: MongoClient[dict[str, Any]]) -> None:
    # An allowed collection read verifies auth as well as connectivity. No data logs.
    client[DATABASE]["users"].find_one({"_id": "foundation-readiness@example.invalid"}, {"_id": 1})
