"""Bounded local HTTP/SSE characterization with real API workers and explicit doubles.

Never connects to Atlas/Engine/providers. Results are not capacity or SLO acceptance.
"""

import argparse
import asyncio
import hashlib
import html
import json
import os
import platform
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/telecom/load/http-mock-v1.json"


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * percent / 100))]


def summarize(values):
    return {
        f"p{p}_ms": round(percentile(values, p) * 1000, 3) if values else None
        for p in (50, 95, 99)
    }


def parse_event(block):
    event, data = None, []
    for line in block.splitlines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            data.append(line[6:])
    return event, json.loads("\n".join(data)) if data else None


def render(report, destination):
    rows = []
    for row in report["stages"]:
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(value))}</td>"
                for value in (
                    row["workers"],
                    row["concurrency"],
                    row["completed"],
                    row["admission_rejected"],
                    row["throughput_rps"],
                    row["first_event"]["p95_ms"],
                    row["complete"]["p95_ms"],
                    row["complete"]["p99_ms"],
                    row["other_user_denials"],
                    len(row["processes"]),
                )
            )
            + "</tr>"
        )
    destination.write_text(
        """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Telecom HTTP characterization</title>
<style>body{font:16px system-ui;
max-width:1100px;margin:40px auto;padding:20px}
table{border-collapse:collapse;width:100%}
td,th{text-align:left;padding:10px;border-bottom:1px solid #ccc}
code{overflow-wrap:anywhere}</style>
<h1>Local HTTP/SSE characterization</h1>
<p>Real API processes; identity and Engine doubles; SQLite fixture state. 
No Atlas, LLM, voice, ingestion, provider cost or production capacity measurement.</p>
<p>Status: """
        + html.escape(report["status"])
        + "</p><p>Commit: <code>"
        + html.escape(report["git_head"])
        + """</code>
</p>
<table>
<thead>
<tr>
<th>Workers</th>
<th>Concurrency</th>
<th>Completed</th>
<th>Rejected</th>
<th>Requests/s</th>
<th>First event p95 ms</th>
<th>Complete p95 ms</th>
<th>Complete p99 ms</th>
<th>Scope denials</th>
<th>Observed processes</th>
</tr>
</thead>
<tbody>"""
        + "".join(rows)
        + "</tbody></table><p>Short closed-loop characterization; "
        "percentiles are descriptive with the listed sample counts. "
        "No SLO or highest stable load claim.</p></html>"
    )


async def exercise(origin, profile, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    records, rejected = [], []
    async with httpx.AsyncClient(
        base_url=origin,
        timeout=profile["timeout_seconds"],
        limits=httpx.Limits(max_connections=concurrency, max_keepalive_connections=0),
        trust_env=False,
    ) as client:

        async def request(index):
            async with semaphore:
                actor = "load-a" if index % 2 == 0 else "load-b"
                other = "load-b" if actor == "load-a" else "load-a"
                headers = {"Origin": origin, "Cookie": "telecom_session=" + actor}
                conversation = str(uuid4())
                started = time.perf_counter()
                first, result, process = None, None, None
                buffer = ""
                async with client.stream(
                    "POST",
                    "/api/journey/chat",
                    headers=headers,
                    json={"conversation_id": conversation, "message": "synthetic load"},
                ) as response:
                    if response.status_code == 503:
                        await response.aread()
                        assert response.json() == {
                            "error": "Server busy; try again later"
                        }
                        rejected.append(index)
                        return
                    assert response.status_code == 200
                    process = response.headers["X-Load-Process"]
                    async for chunk in response.aiter_text():
                        buffer += chunk.replace("\r\n", "\n")
                        while "\n\n" in buffer:
                            block, buffer = buffer.split("\n\n", 1)
                            event, data = parse_event(block)
                            if first is None:
                                first = time.perf_counter() - started
                            assert event != "error", "Unexpected uncertain SSE outcome"
                            if event == "result":
                                assert result is None, "Duplicate SSE result"
                                result = data
                elapsed = time.perf_counter() - started
                assert first is not None and result is not None
                assert (
                    result["text"] == profile["expected_text"]
                    and result["status"] == "completed"
                )
                records.append(
                    {
                        "first": first,
                        "elapsed": elapsed,
                        "process": process,
                        "conversation": conversation,
                        "actor": actor,
                        "other": other,
                        "result": result,
                    }
                )

        # Bounded task set; no request retries and no open-ended load producer.
        tasks = [
            asyncio.create_task(request(i))
            for i in range(concurrency * profile["requests_per_client"])
        ]
        started = time.perf_counter()
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.perf_counter() - started
        # Verify after offered load settles; do not retry an uncertain business request.
        for record in records:
            recovery = await client.post(
                "/api/journey/latest",
                headers={
                    "Origin": origin,
                    "Cookie": "telecom_session=" + record["actor"],
                },
                json={"conversation_id": record["conversation"]},
            )
            assert recovery.status_code == 200 and recovery.json() == record["result"]
            record["recovery_process"] = recovery.headers["X-Load-Process"]
            denial = await client.post(
                "/api/journey/status",
                headers={
                    "Origin": origin,
                    "Cookie": "telecom_session=" + record["other"],
                },
                json={"execution_id": record["result"]["execution_id"]},
            )
            assert denial.status_code == 403
        healthy = await client.get("/healthz")
        assert healthy.status_code == 200
        failed = await client.post(
            "/api/journey/chat",
            headers={"Origin": origin, "Cookie": "telecom_session=load-a"},
            json={"conversation_id": str(uuid4()), "message": "injected-unavailable"},
        )
        assert failed.status_code == 200
        events = [
            parse_event(block)[0]
            for block in failed.text.split("\n\n")
            if block.strip()
        ]
        assert events == ["progress", "error"], "Injected failure reported success"
        return {
            "concurrency": concurrency,
            "offered": len(tasks),
            "completed": len(records),
            "admission_rejected": len(rejected),
            "post_load_health": True,
            "other_user_denials": len(records),
            "recoveries": len(records),
            "injected_failure_correct": True,
            "wall_seconds": round(elapsed, 4),
            "throughput_rps": round(len(records) / elapsed, 3),
            "first_event": summarize([r["first"] for r in records]),
            "complete": summarize([r["elapsed"] for r in records]),
            "processes": sorted({r["process"] for r in records}),
            "cross_process_recoveries": sum(
                r["process"] != r["recovery_process"] for r in records
            ),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = PROFILE.read_bytes()
    profile = json.loads(raw)
    assert profile["workers"] == [1, 2, 4] and profile["concurrency"] == [
        1,
        5,
        10,
        25,
        50,
    ]
    assert profile["requests_per_client"] == 2 and profile["max_wall_seconds"] <= 180
    assert profile["max_chat_requests"] <= 600
    assert (
        sum(profile["concurrency"])
        * profile["requests_per_client"]
        * len(profile["workers"])
        <= profile["max_chat_requests"]
    )
    report = {
        "status": "running",
        "profile": profile,
        "profile_sha256": hashlib.sha256(raw).hexdigest(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "started_at": datetime.now(UTC).isoformat(),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "scripts/run_phase8_http.py",
                "tests/load/http_fixture.py",
                "src/telecom_app/api.py",
                "src/telecom_app/journey.py",
                "src/telecom_app/security.py",
                "src/telecom_app/config.py",
            )
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "loop": "closed",
            "providers": "doubles",
        },
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "stages": [],
        "external_calls": 0,
        "cost_usd": 0,
        "limitations": [
            "No Atlas or real Engine state/SDK/model execution",
            "No production authentication/password hashing workload",
            "No CPU/RAM telemetry, open-loop arrival, soak, OCR or voice workload",
            "Throughput measures chat burst only; scope/recovery checks follow after load",
            "Native session admission and idempotency are not simulated or proved",
        ],
    }
    output = args.output.open("x")

    def save():
        output.seek(0)
        json.dump(report, output, indent=2)
        output.write("\n")
        output.truncate()
        output.flush()

    save()
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="telecom-load-") as temporary:
            state = Path(temporary) / "engine-double.sqlite"
            with sqlite3.connect(state) as store:
                store.execute("PRAGMA journal_mode=WAL")
                store.execute(
                    "CREATE TABLE executions (id TEXT PRIMARY KEY, session TEXT, body TEXT)"
                )
                store.execute("CREATE INDEX session_index ON executions(session)")
            for workers in profile["workers"]:
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1", 0))
                    port = listener.getsockname()[1]
                origin = f"http://127.0.0.1:{port}"
                # Credentials are not inherited. The fixture never loads a dotenv file.
                env = {
                    "PATH": os.environ["PATH"],
                    "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "src"),
                    "TELECOM_LOAD_FIXTURE": "isolated-mock-v1",
                    "TELECOM_LOAD_STATE": str(state),
                    "TELECOM_LOAD_ORIGIN": origin,
                }
                with (Path(temporary) / f"worker-{workers}.log").open("w+") as log:
                    child = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "uvicorn",
                            "tests.load.http_fixture:application",
                            "--factory",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            str(port),
                            "--workers",
                            str(workers),
                            "--no-access-log",
                        ],
                        env=env,
                        cwd=ROOT,
                        stdout=log,
                        stderr=log,
                        start_new_session=True,
                    )
                    try:
                        for _ in range(100):
                            if child.poll() is not None:
                                raise RuntimeError("Fixture exited before readiness")
                            try:
                                with httpx.Client(trust_env=False, timeout=1) as client:
                                    if (
                                        client.get(origin + "/healthz").status_code
                                        == 200
                                    ):
                                        break
                            except httpx.HTTPError:
                                pass
                            time.sleep(0.1)
                        else:
                            raise TimeoutError("Fixture readiness deadline")
                        for concurrency in profile["concurrency"]:
                            remaining = profile["max_wall_seconds"] - (
                                time.monotonic() - started
                            )
                            if remaining <= 0:
                                raise TimeoutError(
                                    "Characterization wall budget exhausted"
                                )

                            async def run():
                                return await asyncio.wait_for(
                                    exercise(origin, profile, concurrency), remaining
                                )

                            result = asyncio.run(run())
                            result["workers"] = workers
                            report["stages"].append(result)
                            save()
                            print(
                                json.dumps(
                                    {
                                        "workers": workers,
                                        "concurrency": concurrency,
                                        "completed": result["completed"],
                                    }
                                ),
                                flush=True,
                            )
                    finally:
                        if child.poll() is None:
                            os.killpg(child.pid, signal.SIGTERM)
                            try:
                                child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid, signal.SIGKILL)
                                child.wait()
        report["status"] = "characterized"
    except Exception as error:
        report["status"] = "stopped"
        report["error_type"] = type(error).__name__
    finally:
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        save()
        output.close()
        render(report, args.output.with_suffix(".html"))
    print(json.dumps({"status": report["status"], "stages": len(report["stages"])}))
    return 0 if report["status"] == "characterized" else 1


if __name__ == "__main__":
    raise SystemExit(main())
