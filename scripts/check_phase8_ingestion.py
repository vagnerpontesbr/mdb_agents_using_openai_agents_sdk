"""Isolated Atlas admission, worker termination and lease fencing; no provider calls."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient

from telecom_app.ingestion import IngestionConflict, MongoIngestion

ROOT = Path(__file__).resolve().parents[1]


def client():
    credentials = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.phase8").read_text().splitlines()
        if line
    )
    # Four submitting threads, one shared pool; no new connection per job.
    return MongoClient(
        "mongodb+srv://openai-sdk.qrmdk.mongodb.net/",
        username="telecom_load_ingestion_worker",
        password=credentials["telecom_load_ingestion_worker"],
        authSource="admin",
        maxPoolSize=5,
        minPoolSize=0,
        timeoutMS=15000,
        appname="telecom-phase8-ingestion",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-tenant")
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "compatibility/phase8-ingestion-evidence.json")
    args = parser.parse_args()
    if args.worker_tenant:
        assert args.worker_tenant.startswith("phase8-") and args.ready_file
        with client() as connection:
            store = MongoIngestion(
                connection.telecom_load_ingestion, load_environment=True
            )
            job = store.claim(args.worker_tenant)
            assert job
            args.ready_file.write_text(
                json.dumps({"id": job["_id"], "lease_token": job["lease_token"]})
            )
            while True:
                time.sleep(1)
    tenant = "phase8-" + uuid4().hex
    report = {
        "status": "running",
        "tenant": tenant,
        "checks": {},
        "provider_calls": 0,
        "limitations": [
            "Worker is terminated after claim, before OCR/provider work",
            "Lease expiry uses injected domain clock, not a six-minute wall wait",
            "Synthetic failed jobs retained only in isolated load namespaces",
        ],
    }
    path = args.output
    output = path.open("x")

    def save():
        output.seek(0)
        json.dump(report, output, indent=2)
        output.write("\n")
        output.truncate()
        output.flush()

    save()
    try:
        with client() as connection:
            clock = [datetime.now(UTC)]
            store = MongoIngestion(
                connection.telecom_load_ingestion,
                clock=lambda: clock[0],
                load_environment=True,
            )
            pdf = (
                b"%PDF-1.4\nSynthetic lease fixture, not an extraction fixture.\n%%EOF"
            )
            with ThreadPoolExecutor(max_workers=4) as pool:
                ids = list(
                    pool.map(
                        lambda _: store.submit(tenant, "same", "1", "a" * 64, pdf),
                        range(4),
                    )
                )
            assert len(set(ids)) == 1
            report["checks"]["concurrent_identical_admission_deduplicated"] = True
            save()

            def submit(i):
                try:
                    return store.submit(tenant, "extra-" + str(i), "1", "a" * 64, pdf)
                except IngestionConflict:
                    return None

            with ThreadPoolExecutor(max_workers=4) as pool:
                extra = list(pool.map(submit, range(6)))
            assert sum(x is not None for x in extra) == 3
            report["checks"]["queue_capped_at_four"] = True
            assert store.claim(tenant + "-other") is None
            report["checks"]["other_tenant_claim_denied"] = True
            save()
            with tempfile.TemporaryDirectory(prefix="phase8-worker-") as directory:
                ready = Path(directory) / "ready.json"
                child = subprocess.Popen(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker-tenant",
                        tenant,
                        "--ready-file",
                        str(ready),
                    ],
                    cwd=ROOT,
                    env={"PATH": os.environ["PATH"]},
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                try:
                    for _ in range(100):
                        if ready.exists():
                            break
                        if child.poll() is not None:
                            raise RuntimeError("Worker failed before claim")
                        time.sleep(0.1)
                    else:
                        raise TimeoutError("Worker did not reach claimed state")
                    first = json.loads(ready.read_text())
                    original = store.db.jobs.find_one(
                        {"_id": first["id"], "tenant_id": tenant}
                    )
                    assert (
                        original["status"] == "running"
                        and original["lease_token"] == first["lease_token"]
                    )
                    child.kill()
                    child.wait(timeout=10)
                    assert child.returncode != 0
                    report["checks"]["real_worker_process_terminated_after_claim"] = (
                        True
                    )
                    save()
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=10)
            assert store.claim(tenant, first["id"]) is None
            clock[0] = original["lease_until"] + timedelta(seconds=1)
            recovered = store.claim(tenant, first["id"])
            assert (
                recovered["attempts"] == 2
                and recovered["lease_token"] != first["lease_token"]
            )
            try:
                store.finish(original, None, failure="worker_failure")
            except IngestionConflict:
                pass
            else:
                raise AssertionError("Terminated worker accepted stale completion")
            report["checks"]["reclaimed_job_fences_stale_worker"] = True
            store.finish(recovered, None, failure="worker_failure")
            try:
                store.finish(recovered, None, failure="worker_failure")
            except IngestionConflict:
                pass
            else:
                raise AssertionError("Duplicate completion admitted")
            report["checks"]["duplicate_finish_denied"] = True
            # Drain only this tenant's remaining jobs, using the second crash budget.
            jobs = [store.claim(tenant) for _ in range(3)]
            assert all(jobs)
            clock[0] += timedelta(seconds=361)
            retry = [store.claim(tenant) for _ in range(3)]
            assert all(j["attempts"] == 2 for j in retry)
            clock[0] += timedelta(seconds=361)
            assert store.claim(tenant) is None
            assert (
                store.expire_exhausted(tenant) == 3
                and store.expire_exhausted(tenant) == 0
            )
            assert (
                store.db.staged_artifacts.find_one({"_id": "quota:" + tenant})["active"]
                == 0
            )
            report["checks"]["attempt_budget_and_exact_quota_release"] = True
            report["status"] = "passed"
    except Exception as error:
        report["status"] = "stopped"
        report["error_type"] = type(error).__name__
    finally:
        save()
        output.close()
    print(json.dumps(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
