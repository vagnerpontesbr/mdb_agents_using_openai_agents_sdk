"""Read-only five-minute native hybrid/governance profile over the isolated revoked fixture."""

import argparse
import asyncio
import json
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from pymongo import MongoClient

from telecom_app.knowledge import Scope
from telecom_app.knowledge_authority import MongoKnowledgeAuthority
from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_search import hybrid_pipeline, retrieve

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "No currently approved procedure matches your access and equipment. Contact support."


async def run(report, save):
    source = json.loads((ROOT / "compatibility/phase8-cache-concurrency.json").read_text())
    assert source["status"] == "passed"
    tenant = source["tenant"]
    assert tenant.startswith("phase8-cache-") and len(tenant) == 45
    report["tenant"] = tenant
    credentials = dict(
        line.split("=", 1) for line in (ROOT / ".env.phase8").read_text().splitlines() if line
    )
    with MongoClient(
        "mongodb+srv://openai-sdk.qrmdk.mongodb.net/",
        username="telecom_load_knowledge_reader",
        password=credentials["telecom_load_knowledge_reader"],
        authSource="admin",
        maxPoolSize=4,
        minPoolSize=0,
        timeoutMS=15000,
        appname="telecom-phase8-read-profile",
    ) as client:
        reader = MongoKnowledgeReader(client.telecom_load_knowledge, load_environment=True)
        authority = MongoKnowledgeAuthority(client.telecom_load_knowledge, load_environment=True)
        scope = Scope(tenant, frozenset({"synthetic-support"}), "FiberBox", "demo", "2.x")
        vector = [0.1] * 1024
        query = "optical cable"

        class NoRank:
            def rank(self, query, texts):
                raise AssertionError("Revoked source must never reach reranking")

        def positive():
            candidates = reader.search(hybrid_pipeline(scope, query, vector, datetime.now(UTC)))
            assert len(candidates) == 1
            row = reader.version(tenant, candidates[0].version_key)
            assert row is not None and row.status == "revoked"
            return True

        # The deliberately stale chunk stays indexed; authoritative revocation must win.
        report["stale_index_positive_control"] = await asyncio.to_thread(positive)
        save()
        active = set()
        errors = []
        began = time.monotonic()

        def read(index):
            tick = time.monotonic()
            selected = (
                scope
                if index % 3 == 0
                else replace(scope, tenant_id=tenant + "-other")
                if index % 3 == 1
                else replace(scope, readers=frozenset({"other"}))
            )
            assert retrieve(reader, authority, NoRank(), selected, query, vector) == REFUSAL
            return (time.monotonic() - tick) * 1000

        async def request(index):
            try:
                latency = await asyncio.to_thread(read, index)
                report["latencies_ms"].append(round(latency, 3))
                report["completed"] += 1
            except Exception as error:
                errors.append(type(error).__name__)
                report["errors"] += 1

        for index in range(300):
            await asyncio.sleep(max(0, began + index - time.monotonic()))
            if errors:
                raise AssertionError("Read invariant failed: " + errors[0])
            assert len(active) < 4, "Arrival rate exceeded the four-operation bound"
            report["offered"] += 1
            task = asyncio.create_task(request(index))
            active.add(task)
            task.add_done_callback(active.discard)
            if index % 30 == 0:
                save()
        if active:
            await asyncio.gather(*list(active))
        await asyncio.sleep(max(0, began + 300 - time.monotonic()))
        assert not errors and report["completed"] == 300
        values = sorted(report["latencies_ms"])
        report["p95_ms"] = values[284]
        report["wall_seconds"] = round(time.monotonic() - began, 3)
        assert report["p95_ms"] <= 5000
        assert await asyncio.to_thread(positive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "profile": {
            "seconds": 300,
            "rps": 1,
            "max_inflight": 4,
            "operation_timeout_ms": 15000,
            "p95_limit_ms": 5000,
            "max_wall_seconds": 360,
            "expected_errors": 0,
        },
        "environment_evidence": "phase8-environment-evidence.json",
        "offered": 0,
        "completed": 0,
        "errors": 0,
        "latencies_ms": [],
        "provider_calls": 0,
        "limitations": [
            "One existing synthetic source; not representative corpus capacity",
            "100 revoked-source, 100 other-tenant and 100 other-ACL reads",
            "Read-only native hybrid fusion and backend governance, no embeddings or reranking calls",
            "Local generator runs concurrently with the local HTTP soak",
            "Shared M20 cluster resource saturation and peak throughput are not measured",
        ],
    }
    with args.output.open("x") as output:

        def save():
            output.seek(0)
            json.dump(report, output, indent=2)
            output.write("\n")
            output.truncate()
            output.flush()

        save()
        try:

            async def bounded():
                await asyncio.wait_for(run(report, save), 360)

            asyncio.run(bounded())
            report["status"] = "passed"
        except Exception as error:
            report["status"] = "stopped"
            report["error_type"] = type(error).__name__
        save()
    print(json.dumps({k: report.get(k) for k in ("status", "completed", "p95_ms")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
