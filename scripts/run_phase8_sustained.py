"""Bounded local sustained/SSE/voice transport and offline Docling contention profile."""

import argparse
import asyncio
import base64
import hashlib
import html
import io
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
import wave
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from run_phase8_http import parse_event, summarize

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/telecom/load/sustained-v1.json"
TEXT = "Synthetic transport response."
PCM = base64.b64encode(b"\x00\x04\x00\xfc" * 3000).decode()


def processes(api_pid, ingestion_pids):
    raw = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss=,pcpu="], text=True)
    rows = {}
    for line in raw.splitlines():
        pid, parent, rss, cpu = line.split()
        rows[int(pid)] = (int(parent), int(rss) / 1024, float(cpu))

    def tree(root):
        chosen = {root}
        while True:
            extra = {pid for pid, row in rows.items() if row[0] in chosen}
            if extra <= chosen:
                break
            chosen |= extra
        return chosen & rows.keys()

    api = tree(api_pid)
    ingestion = set()
    for pid in ingestion_pids:
        ingestion |= tree(pid)

    def rss(group):
        return round(sum(rows[pid][1] for pid in group), 3)

    return {
        "api_rss_mb": rss(api),
        "api_cpu_percent_ps": round(sum(rows[p][2] for p in api), 2),
        "generator_rss_mb": rows[os.getpid()][1],
        "generator_cpu_percent_ps": rows[os.getpid()][2],
        "ingestion_rss_mb": rss(ingestion),
        "api_process_count": len(api),
    }


def render(report, path):
    rows = "".join(
        "<tr>"
        + "".join(
            "<td>" + html.escape(str(w.get(k, ""))) + "</td>"
            for k in (
                "name",
                "seconds",
                "offered",
                "completed",
                "admission_rejected",
                "generator_drops",
                "chat_p95_ms",
                "voice_p95_ms",
                "first_event_p95_ms",
                "passed",
            )
        )
        + "</tr>"
        for w in report["windows"]
    )
    samples = report["samples"]
    maximum = max([s["api_rss_mb"] for s in samples] + [1])
    last = max([s["elapsed"] for s in samples] + [1])
    points = " ".join(
        f"{30 + s['elapsed'] / last * 900:.1f},{210 - s['api_rss_mb'] / maximum * 180:.1f}"
        for s in samples
    )
    path.write_text(
        """<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 8 sustained profile</title>
<style>body{font:16px system-ui;margin:30px auto;max-width:1200px;padding:20px}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccc}table{border-collapse:collapse}svg{width:100%;height:240px}</style>
<h1>Phase 8 local sustained profile</h1><p>Real API processes and CPU Docling; identity, Engine and speech providers are doubles. No Atlas or paid model throughput claim.</p>"""
        + "<p>Status: "
        + html.escape(report["status"])
        + "</p><table><tr><th>Window</th><th>Seconds</th><th>Offered</th><th>Completed</th><th>Rejected</th><th>Generator drops</th><th>Chat p95 ms</th><th>Voice p95 ms</th><th>First SSE p95 ms</th><th>Passed</th></tr>"
        + rows
        + "</table>"
        + f'<h2>API resident memory</h2><p>Peak {maximum:.1f} MiB; observed duration {last:.0f}s.</p><svg viewBox="0 0 960 240" role="img" aria-label="API resident memory over elapsed time"><polyline fill="none" stroke="#00684a" stroke-width="2" points="{points}"/></svg>'
        + "<p>Raw samples and thresholds are in the adjacent JSON. PCM is a synthetic tone, not speech. OS ps CPU percentages are sampled indicators; they are not billing data.</p></html>"
    )


async def run(profile, report, save, origin, api_pid, directory):
    stopped = asyncio.Event()
    ingestion_pids = set()
    start = time.monotonic()
    thresholds = profile["thresholds"]
    async with httpx.AsyncClient(
        base_url=origin,
        timeout=profile["request_timeout_seconds"],
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        trust_env=False,
    ) as client:

        async def sample():
            while not stopped.is_set():
                sample = await asyncio.to_thread(
                    processes, api_pid, set(ingestion_pids)
                )
                sample["elapsed"] = round(time.monotonic() - start, 3)
                response = await client.get("/_load/metrics")
                sample["loop_lag_ms"] = (
                    response.json().get("loop_lag_ms")
                    if response.status_code == 200
                    else None
                )
                report["samples"].append(sample)
                for field, limit in [
                    ("api_rss_mb", "api_rss_limit_mb"),
                    ("generator_rss_mb", "generator_rss_limit_mb"),
                    ("ingestion_rss_mb", "ingestion_rss_limit_mb"),
                ]:
                    if sample[field] > thresholds[limit]:
                        raise AssertionError("Resource ceiling: " + field)
                save()
                try:
                    await asyncio.wait_for(stopped.wait(), profile["sampling_seconds"])
                except TimeoutError:
                    pass

        sampler = asyncio.create_task(sample())

        async def job_loop(stop):
            count = 0
            while not stop.is_set() and count < thresholds["ingestion_max_jobs"]:
                scanned = count % 2 == 1
                source = (
                    ROOT
                    / "artifacts/compatibility/pdf"
                    / ("scanned.pdf" if scanned else "text.pdf")
                )
                target = directory / f"extracted-{count}.json"
                command = [
                    str(ROOT / "compatibility/ingestion-runtime/.venv/bin/python"),
                    str(ROOT / "scripts/extract_knowledge_pdf.py"),
                    str(source),
                    "--output",
                    str(target),
                    "--child",
                    "--allow-model-downloads",
                ]
                if scanned:
                    command.append("--scanned")
                env = {
                    "PATH": os.environ["PATH"],
                    "HOME": os.environ["HOME"],
                    "HF_HUB_OFFLINE": "1",
                    "TRANSFORMERS_OFFLINE": "1",
                    "TOKENIZERS_PARALLELISM": "false",
                    "OMP_NUM_THREADS": "2",
                }
                child = subprocess.Popen(
                    command,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                ingestion_pids.add(child.pid)
                began = time.monotonic()
                try:
                    code = await asyncio.to_thread(
                        child.wait, thresholds["ingestion_job_seconds"]
                    )
                    if code != 0:
                        raise RuntimeError("Offline Docling conversion failed")
                    data = json.loads(target.read_text())
                    assert (
                        data["contract"] == "telecom-pdf-pages-v1"
                        and data["ocr"] == scanned
                    )
                    assert (
                        data["checksum"]
                        == hashlib.sha256(source.read_bytes()).hexdigest()
                    )
                    assert data["pages"] and all(text.strip() for text in data["pages"])
                    report["ingestion_jobs"].append(
                        {
                            "scanned": scanned,
                            "pages": len(data["pages"]),
                            "seconds": round(time.monotonic() - began, 3),
                            "source_sha256": data["checksum"],
                        }
                    )
                    target.unlink()
                    count += 1
                    save()
                finally:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                        await asyncio.to_thread(child.wait)
                    ingestion_pids.discard(child.pid)

        try:
            for spec in profile["windows"]:
                if sampler.done():
                    await sampler
                window = {
                    "name": spec["name"],
                    "seconds": spec["seconds"],
                    "rps": spec["rps"],
                    "offered": 0,
                    "completed": 0,
                    "admission_rejected": 0,
                    "generator_drops": 0,
                    "errors": 0,
                    "scope_checks": 0,
                    "cross_process_recoveries": 0,
                    "processes": [],
                }
                report["windows"].append(window)
                save()
                latencies = {"chat": [], "voice": [], "first": [], "launch_lag": []}
                active = set()
                completed = []
                errors = []
                seen = set()

                async def journey(index, scheduled):
                    t = time.monotonic()
                    latencies["launch_lag"].append(t - scheduled)
                    actor = "load-a" if index % 2 == 0 else "load-b"
                    other = "load-b" if actor == "load-a" else "load-a"
                    headers = {"Origin": origin, "Cookie": "telecom_session=" + actor}
                    voice = bool(
                        spec["voice_every"] and index % spec["voice_every"] == 0
                    )
                    conversation = str(uuid4())
                    try:
                        if voice:
                            response = await client.post(
                                "/api/voice/transcribe",
                                headers=headers,
                                json={"pcm_base64": PCM},
                            )
                            assert response.status_code == 200 and response.json() == {
                                "text": "Synthetic transport request."
                            }
                        chat_start = time.monotonic()
                        first = None
                        result = None
                        buffer = ""
                        async with client.stream(
                            "POST",
                            "/api/journey/chat",
                            headers=headers,
                            json={
                                "conversation_id": conversation,
                                "message": "synthetic sustained load",
                            },
                        ) as response:
                            if response.status_code == 503:
                                await response.aread()
                                assert response.json() == {
                                    "error": "Server busy; try again later"
                                }
                                window["admission_rejected"] += 1
                                return
                            assert response.status_code == 200
                            pid = response.headers["X-Load-Process"]
                            seen.add(pid)
                            async for chunk in response.aiter_text():
                                buffer += chunk.replace("\r\n", "\n")
                                while "\n\n" in buffer:
                                    block, buffer = buffer.split("\n\n", 1)
                                    event, data = parse_event(block)
                                    if first is None:
                                        first = time.monotonic() - chat_start
                                    assert event != "error"
                                    if event == "result":
                                        assert result is None
                                        result = data
                        assert (
                            result
                            and result["status"] == "completed"
                            and result["text"] == TEXT
                            and first is not None
                        )
                        if voice:
                            response = await client.post(
                                "/api/voice/speak",
                                headers=headers,
                                json={"execution_id": result["execution_id"]},
                            )
                            assert (
                                response.status_code == 200
                                and response.headers["content-type"] == "audio/wav"
                            )
                            with wave.open(io.BytesIO(response.content), "rb") as wav:
                                assert (
                                    wav.getnchannels(),
                                    wav.getsampwidth(),
                                    wav.getframerate(),
                                    wav.getnframes(),
                                ) == (1, 2, 24000, 6000)
                        latencies["first"].append(first)
                        latencies["voice" if voice else "chat"].append(
                            time.monotonic() - t
                        )
                        window["completed"] += 1
                        # Bounded post-window sample; the spike still checks every successful response text.
                        if index % 10 == 0:
                            completed.append(
                                (headers, other, conversation, result, pid)
                            )
                    except Exception as error:
                        window["errors"] += 1
                        errors.append(type(error).__name__)

                began = time.monotonic()
                stop_ingestion = asyncio.Event()
                ingestion = None
                if spec.get("docling"):
                    ingestion = asyncio.create_task(job_loop(stop_ingestion))
                try:
                    total = int(spec["seconds"] * spec["rps"])
                    for index in range(total):
                        if errors:
                            raise AssertionError("Journey invariant failed")
                        if sampler.done():
                            await sampler
                        if ingestion and ingestion.done():
                            await ingestion
                        scheduled = began + index / spec["rps"]
                        await asyncio.sleep(max(0, scheduled - time.monotonic()))
                        window["offered"] += 1
                        if len(active) >= profile["max_inflight"]:
                            window["generator_drops"] += 1
                            continue
                        task = asyncio.create_task(journey(index, scheduled))
                        active.add(task)
                        task.add_done_callback(active.discard)
                    drain = time.monotonic()
                    if active:
                        await asyncio.wait_for(
                            asyncio.gather(*list(active)),
                            thresholds["recovery_drain_seconds"],
                        )
                    window["drain_seconds"] = round(time.monotonic() - drain, 3)
                    # Hold to the declared duration even when the last response completes before its end.
                    await asyncio.sleep(
                        max(0, began + spec["seconds"] - time.monotonic())
                    )
                finally:
                    for task in active:
                        task.cancel()
                    if active:
                        await asyncio.gather(*list(active), return_exceptions=True)
                    stop_ingestion.set()
                    if ingestion:
                        await ingestion
                for headers, other, conversation, result, pid in completed:
                    response = await client.post(
                        "/api/journey/latest",
                        headers=headers,
                        json={"conversation_id": conversation},
                    )
                    assert response.status_code == 200 and response.json() == result
                    window["cross_process_recoveries"] += (
                        response.headers["X-Load-Process"] != pid
                    )
                    denied = await client.post(
                        "/api/journey/status",
                        headers={
                            "Origin": origin,
                            "Cookie": "telecom_session=" + other,
                        },
                        json={"execution_id": result["execution_id"]},
                    )
                    assert denied.status_code == 403
                    window["scope_checks"] += 1
                window.update(
                    chat_p95_ms=summarize(latencies["chat"])["p95_ms"],
                    voice_p95_ms=summarize(latencies["voice"])["p95_ms"],
                    first_event_p95_ms=summarize(latencies["first"])["p95_ms"],
                    launch_lag_p95_ms=summarize(latencies["launch_lag"])["p95_ms"],
                    processes=sorted(seen),
                )
                normal = not spec.get("allow_rejection", False)
                passed = (
                    not errors
                    and window["completed"]
                    + window["admission_rejected"]
                    + window["generator_drops"]
                    == window["offered"]
                )
                if normal:
                    passed &= (
                        window["admission_rejected"] == 0
                        and window["generator_drops"] == 0
                    )
                    for key in ("chat_p95_ms", "voice_p95_ms", "first_event_p95_ms"):
                        passed &= window[key] is None or window[key] <= thresholds[key]
                window["passed"] = bool(passed)
                save()
                print(
                    json.dumps(
                        {
                            k: window[k]
                            for k in (
                                "name",
                                "offered",
                                "completed",
                                "admission_rejected",
                                "passed",
                            )
                        }
                    ),
                    flush=True,
                )
                if not passed:
                    raise AssertionError("Window threshold failed")
                if spec["name"] == "warmup":
                    report["post_warmup_api_rss_mb"] = report["samples"][-1][
                        "api_rss_mb"
                    ]
            samples = report["samples"]
            warm = profile["windows"][0]["seconds"]
            steady = [s for s in samples if s["elapsed"] >= warm]
            growth = (
                max(s["api_rss_mb"] for s in steady) - report["post_warmup_api_rss_mb"]
            )
            lag = [
                s["loop_lag_ms"] / 1000 for s in samples if s["loop_lag_ms"] is not None
            ]
            report["checks"] = {
                "api_rss_growth_mb": round(growth, 3),
                "loop_lag_p95_ms": summarize(lag)["p95_ms"],
                "text_and_scanned_ingestion": {
                    j["scanned"] for j in report["ingestion_jobs"]
                }
                == {True, False},
                "all_windows_passed": all(w["passed"] for w in report["windows"]),
            }
            assert growth <= thresholds["api_rss_growth_after_warmup_mb"]
            assert report["checks"]["loop_lag_p95_ms"] <= thresholds["loop_lag_p95_ms"]
            if not report["smoke"]:
                assert report["checks"]["text_and_scanned_ingestion"]
        finally:
            stopped.set()
            await sampler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    raw = PROFILE.read_bytes()
    profile = json.loads(raw)
    assert (
        sum(s["seconds"] * s["rps"] for s in profile["windows"])
        <= profile["max_journeys"]
        <= 16000
    )
    if args.smoke:
        for w in profile["windows"]:
            w["seconds"] = 3
            w["rps"] = 5 if w["name"] != "spike" else 50
        profile["windows"][-1]["seconds"] = 5
        profile["sampling_seconds"] = 1
        profile["thresholds"]["ingestion_max_jobs"] = 1
    report = {
        "status": "running",
        "smoke": args.smoke,
        "profile": profile,
        "profile_sha256": hashlib.sha256(raw).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "scripts/run_phase8_sustained.py",
                "tests/load/http_fixture.py",
                "scripts/extract_knowledge_pdf.py",
                "uv.lock",
                "compatibility/ingestion-runtime/uv.lock",
            )
        },
        "windows": [],
        "samples": [],
        "ingestion_jobs": [],
        "external_provider_calls": 0,
        "provider_cost_usd": 0,
    }
    output = args.output.open("x")

    def save():
        output.seek(0)
        json.dump(report, output, indent=2)
        output.write("\n")
        output.truncate()
        output.flush()

    save()
    began = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="telecom-sustained-") as temp:
            directory = Path(temp)
            state = directory / "engine.sqlite"
            with sqlite3.connect(state) as db:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute(
                    "CREATE TABLE executions (id TEXT PRIMARY KEY, session TEXT, body TEXT)"
                )
                db.execute("CREATE INDEX session_index ON executions(session)")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            origin = f"http://127.0.0.1:{port}"
            env = {
                "PATH": os.environ["PATH"],
                "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "src"),
                "TELECOM_LOAD_FIXTURE": "isolated-mock-v1",
                "TELECOM_LOAD_STATE": str(state),
                "TELECOM_LOAD_ORIGIN": origin,
                "TELECOM_LOAD_VOICE": "true",
            }
            with (directory / "api.log").open("w") as log:
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
                        str(profile["workers"]),
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
                            raise RuntimeError("API exited before readiness")
                        try:
                            with httpx.Client(trust_env=False, timeout=1) as client:
                                if client.get(origin + "/healthz").status_code == 200:
                                    break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.1)
                    else:
                        raise TimeoutError("Readiness deadline")

                    async def execute():
                        await asyncio.wait_for(
                            run(profile, report, save, origin, child.pid, directory),
                            profile["max_wall_seconds"],
                        )

                    asyncio.run(execute())
                finally:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait()
        report["status"] = "smoke_passed" if args.smoke else "passed"
    except Exception as error:
        report["status"] = "stopped"
        report["error_type"] = type(error).__name__
        report["failure_reason"] = (
            str(error)
            if isinstance(error, (AssertionError, RuntimeError, TimeoutError))
            else "Sanitized unexpected failure"
        )
    finally:
        report["wall_seconds"] = round(time.monotonic() - began, 3)
        save()
        output.close()
        render(report, args.output.with_suffix(".html"))
    print(
        json.dumps({"status": report["status"], "wall_seconds": report["wall_seconds"]})
    )
    return 0 if report["status"] in ("passed", "smoke_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
