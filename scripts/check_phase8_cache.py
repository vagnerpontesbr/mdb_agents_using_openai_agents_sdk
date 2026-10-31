"""Real Atlas cache/source interleaving; synthetic vectors and controlled reranker."""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pymongo import MongoClient

from telecom_app.knowledge_authority import (
    MongoKnowledgeAuthority,
    document_key,
    version_key,
)
from telecom_app.knowledge_cache import MongoCandidateCache
from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_search import PROFILE, Candidate, retrieve
from tests.foundation.test_knowledge import SCOPE, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "compatibility/phase8-cache-concurrency.json")
    args = parser.parse_args()
    path = args.output
    output = path.open("x")
    tenant = "phase8-cache-" + uuid4().hex
    scope = replace(SCOPE, tenant_id=tenant)
    now = datetime.now(UTC).replace(microsecond=0)
    report = {
        "status": "running",
        "tenant": tenant,
        "checks": {},
        "provider_calls": 0,
        "limitations": [
            "Synthetic vectors do not measure embedding/retrieval quality",
            "Reranking uses a controlled barrier, not a provider call",
            "Synthetic approval receipts are fixtures, not new native-review evidence",
            "Fixtures remain only in isolated load namespaces",
        ],
    }

    def save():
        output.seek(0)
        json.dump(report, output, indent=2)
        output.write("\n")
        output.truncate()
        output.flush()

    save()
    try:
        credentials = dict(
            line.split("=", 1)
            for line in (ROOT / ".env.phase8").read_text().splitlines()
            if line
        )
        with ExitStack() as stack:

            def connect(user):
                # Four concurrent readers, one reused client per domain, no per-query clients.
                return stack.enter_context(
                    MongoClient(
                        "mongodb+srv://openai-sdk.qrmdk.mongodb.net/",
                        username=user,
                        password=credentials[user],
                        authSource="admin",
                        maxPoolSize=5,
                        minPoolSize=0,
                        timeoutMS=15000,
                        appname="telecom-phase8-cache",
                    )
                )

            reader_client = connect("telecom_load_knowledge_reader")
            publisher = connect(
                "telecom_load_knowledge_publisher"
            ).telecom_load_knowledge
            cache_client = connect("telecom_load_cache")
            v = version(tenant_id=tenant, ingested_at=now)
            key = version_key(v)
            text = "Synthetic load procedure: inspect the optical cable."
            chunk = Candidate(
                chunk_id="c1",
                version_key=key,
                revision=1,
                text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                pages=(1,),
            )
            fields = v.model_dump(mode="python")
            # Provision one owner fixture with the operator; runtime roles stay read-only for owners.
            with MongoClient(
                os.environ["MONGODB_URI"], timeoutMS=15000, maxPoolSize=1
            ) as admin:
                admin.telecom_load_knowledge.owners.insert_one(
                    {
                        "_id": tenant + ":owner",
                        "tenant_id": tenant,
                        "owner_id": v.information_owner,
                        "active": True,
                        "user_ids": [v.approved_by],
                    }
                )
            publisher.document_versions.insert_one({"_id": key, **fields})
            publisher.documents.insert_one(
                {
                    "_id": document_key(tenant, v.document_id),
                    "tenant_id": tenant,
                    "document_id": v.document_id,
                    "version_key": key,
                    "version_id": v.version_id,
                    "revision": 1,
                    "conflict": False,
                }
            )
            publisher.review_events.insert_one(
                {
                    "_id": uuid4().hex * 2,
                    "tenant_id": tenant,
                    "execution_id": "synthetic-load-receipt",
                    "action_digest": "a" * 64,
                    "version_key": key,
                    "metadata_digest": v.approval_digest(),
                    "actor": v.approved_by,
                    "source_checksum": v.checksum,
                    "job_id": "b" * 64,
                    "recorded_at": now,
                }
            )
            publisher.chunks.insert_one(
                {
                    "_id": key,
                    **chunk.model_dump(mode="python"),
                    **{
                        name: fields[name]
                        for name in (
                            "tenant_id",
                            "acl",
                            "product",
                            "region",
                            "firmware_range",
                            "language",
                            "status",
                            "effective_from",
                            "expires_at",
                            "review_due_at",
                        )
                    },
                    "embedding_profile": PROFILE,
                    "eligible": True,
                    "embedding": [0.1] * 1024,
                }
            )
            reader = MongoKnowledgeReader(
                reader_client.telecom_load_knowledge, load_environment=True
            )
            authority = MongoKnowledgeAuthority(
                reader_client.telecom_load_knowledge, load_environment=True
            )
            cache = MongoCandidateCache(
                cache_client.telecom_load_knowledge, reader, load_environment=True
            )
            cache.store(scope, "optical cable", [0.1] * 1024, [chunk], now)
            for _ in range(30):
                if cache.lookup(scope, "optical cable", [0.1] * 1024, now):
                    break
                time.sleep(2)
            else:
                raise TimeoutError("Cache not visible in native vector index")

            class Rank:
                def rank(self, query, documents):
                    return [0]

            answer = retrieve(
                reader,
                authority,
                Rank(),
                scope,
                "optical cable",
                [0.1] * 1024,
                lambda: now,
                cache=cache,
            )
            assert answer == text + "\n[SOP-ONT, version 2, pages 1]"
            report["checks"]["native_cache_positive_control"] = True
            assert (
                cache.lookup(
                    replace(scope, tenant_id=tenant + "-other"),
                    "optical cable",
                    [0.1] * 1024,
                    now,
                )
                is None
            )
            assert (
                cache.lookup(
                    replace(scope, readers=frozenset({"other"})),
                    "optical cable",
                    [0.1] * 1024,
                    now,
                )
                is None
            )
            report["checks"]["tenant_and_acl_cache_denials"] = True
            save()
            ready = threading.Barrier(5)
            release = threading.Event()

            class PausedRank:
                def rank(self, query, documents):
                    ready.wait(timeout=30)
                    assert release.wait(timeout=30)
                    return [0]

            def query(_):
                return retrieve(
                    reader,
                    authority,
                    PausedRank(),
                    scope,
                    "optical cable",
                    [0.1] * 1024,
                    lambda: now,
                    cache=cache,
                )

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(query, i) for i in range(4)]
                try:
                    ready.wait(timeout=30)
                    changed = publisher.document_versions.update_one(
                        {"_id": key, "tenant_id": tenant},
                        {"$set": {"status": "revoked"}},
                    )
                    assert changed.modified_count == 1
                finally:
                    release.set()
                results = [future.result(timeout=30) for future in futures]
            assert all(
                text not in result
                and result
                == "The procedure changed before release. Contact support for current guidance."
                for result in results
            )
            report["checks"][
                "four_inflight_cache_responses_blocked_after_revocation"
            ] = True
            report["status"] = "passed"
    except Exception as error:
        report["status"] = "stopped"
        report["error_type"] = type(error).__name__
        report["error_code"] = getattr(error, "code", None)
    finally:
        save()
        output.close()
    print(json.dumps(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
