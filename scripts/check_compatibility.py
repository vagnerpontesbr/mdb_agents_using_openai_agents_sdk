"""Phase 0 evidence: offline metadata/import checks and explicit bounded live probes.

Exit 0: requested checks pass; 1: failure; 2: prerequisites blocked.
Passing a selected probe never means the entire phase is complete.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TARGET = "3.15.2"
PACKAGES = {
    "openai-agents": "agents",
    "pymongo": "pymongo",
    "docling": "docling.document_converter",
    "agent-engine-sdk-memory": "agent_engine_sdk_memory",
}
ENV_NAMES = (
    "OPENAI_API_KEY", "OPENAI_MODEL", "VOYAGE_API_KEY", "MONGODB_URI",
    "ATLAS_CLUSTER_HOST", "AGENT_ENGINE_URL", "AGENT_ENGINE_PROJECT_ID",
    "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN",
)


def numeric_version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+(?:\.\d+){0,2}", value):
        raise ValueError("Only numeric stable versions are supported by this metadata check")
    return tuple((list(map(int, value.split("."))) + [0, 0])[:3])


def allows_python(specification: str, target: str) -> bool:
    """Evaluate only the simple bounds present in the captured Requires-Python fields.

    Unknown PEP 440 expressions are rejected rather than guessed. uv remains the
    authoritative dependency resolver, including all transitive requirements.
    """
    version = numeric_version(target)
    clauses = specification.split(",")
    results = []
    for clause in clauses:
        match = re.fullmatch(r"\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,2})\s*", clause)
        if not match:
            raise ValueError("Unsupported metadata constraint; use uv for resolution")
        operator, raw = match.groups()
        bound = numeric_version(raw)
        results.append({">=": version >= bound, "<=": version <= bound,
                        "==": version == bound, "!=": version != bound,
                        ">": version > bound, "<": version < bound}[operator])
    return all(results)


def result(check: str, status: str, detail: str, **evidence: object) -> dict:
    return {"check": check, "status": status, "detail": detail, **evidence}


def metadata_checks(target: str) -> list[dict]:
    snapshot = json.loads((ROOT / "compatibility/package-metadata.json").read_text())
    checks = []
    for package in snapshot["packages"]:
        constraint = package.get("requires_python") or ""
        if package["name"] == "voyageai":
            checks.append(result("voyageai.metadata", "excluded",
                                 "Python SDK rejected for <3.15 bound; official HTTP API selected instead",
                                 version=package["version"], requires_python=constraint))
            continue
        try:
            allowed = allows_python(constraint, target)
        except ValueError:
            checks.append(result(package["name"] + ".metadata", "blocked", "Constraint needs full resolver"))
            continue
        checks.append(result(
            package["name"] + ".metadata", "pass" if allowed else "fail",
            "Published Python bound only; not an install/import test",
            version=package["version"], requires_python=constraint,
            target_python=target, source=package["source"],
        ))
    return checks


def import_checks() -> list[dict]:
    checks = []
    for distribution, module in PACKAGES.items():
        try:
            version = metadata.version(distribution)
            importlib.import_module(module)
            checks.append(result(distribution + ".import", "pass", "Import succeeded", version=version))
        except metadata.PackageNotFoundError:
            checks.append(result(distribution + ".import", "blocked", "Distribution not installed"))
        except Exception as exc:
            # Exception text may contain URLs/credentials; never emit it.
            checks.append(result(distribution + ".import", "fail", "Import failed", error_class=type(exc).__name__))
    return checks


def need_env(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not os.environ.get(name, "").strip()]


def probe_mongodb() -> dict:
    missing = need_env(("MONGODB_URI", "ATLAS_CLUSTER_HOST"))
    if missing:
        return result("mongodb.live", "blocked", "Required configuration missing", missing=missing)
    uri = os.environ["MONGODB_URI"]
    parsed = urlsplit(uri)
    expected = os.environ["ATLAS_CLUSTER_HOST"].strip().lower()
    if parsed.scheme != "mongodb+srv" or (parsed.hostname or "").lower() != expected:
        return result("mongodb.live", "fail", "Expected Atlas SRV host does not match configuration")
    from pymongo import MongoClient

    # A single sequential diagnostic, not production pool sizing. Monitoring
    # connections are additional; a 10-second operation budget bounds failures.
    with MongoClient(uri, appname="telecom-phase0", maxPoolSize=1, minPoolSize=0,
                     serverSelectionTimeoutMS=10000, timeoutMS=10000) as client:
        client.admin.command("ping")
        info = client.admin.command("buildInfo")
    version = str(info.get("version", "unknown"))
    return result("mongodb.live", "pass" if version.split(".")[0] == "9" else "fail",
                  "Ping/buildInfo only; no search, roles, writes, or Engine attachment proven", server_version=version)


def probe_openai() -> dict:
    missing = need_env(("OPENAI_API_KEY", "OPENAI_MODEL"))
    if missing:
        return result("openai.live", "blocked", "Required configuration missing", missing=missing)
    from agents import Agent, ModelSettings, RunConfig, Runner, function_tool
    from openai import AsyncOpenAI
    from agents import OpenAIResponsesModel

    called = []

    @function_tool
    def lookup_demo_invoice() -> str:
        """Return the synthetic invoice amount; this tool has no side effects."""
        called.append(True)
        return "USD 79.90"

    async def run() -> bool:
        import asyncio
        async with AsyncOpenAI(timeout=20, max_retries=0) as client:
            agent = Agent(
                name="Phase0InvoiceProbe",
                instructions="Call lookup_demo_invoice once for this synthetic request.",
                model=OpenAIResponsesModel(model=os.environ["OPENAI_MODEL"], openai_client=client),
                tools=[lookup_demo_invoice],
                model_settings=ModelSettings(tool_choice="lookup_demo_invoice", parallel_tool_calls=False),
                tool_use_behavior="stop_on_first_tool",
            )
            output = await asyncio.wait_for(Runner.run(
                agent, "Read the synthetic invoice.", max_turns=2,
                run_config=RunConfig(tracing_disabled=True),
            ), timeout=30)
            return len(called) == 1 and output.final_output == "USD 79.90"

    import asyncio
    passed = asyncio.run(run())
    return result("openai.live", "pass" if passed else "fail",
                  "Real model function selection and synthetic tool output only; not application authorization")


def run_live(probe: str, allowed: bool) -> dict:
    if not allowed:
        return result(probe + ".live", "blocked", "Live probe requires --allow-live")
    try:
        return {"mongodb": probe_mongodb, "openai": probe_openai, "voyage": probe_voyage,
                "engine": probe_engine, "engine-context": probe_engine_context,
                "engine-auth": probe_engine_auth}[probe]()
    except ImportError:
        return result(probe + ".live", "blocked", "Required SDK dependency unavailable")
    except Exception as exc:
        return probe_failure(probe, exc)


def probe_failure(probe: str, exc: Exception, **evidence: object) -> dict:
    status = getattr(exc, "status", getattr(exc, "status_code", None))
    code = getattr(exc, "code", None)
    return result(probe + ".live", "fail", "Probe failed; sensitive exception text suppressed",
                  error_class=type(exc).__name__,
                  error_code=code if code in ("INVALID_TOKEN", "TOKEN_EXPIRED", "UNAUTHORIZED", "FORBIDDEN") else None,
                  http_status=status if type(status) is int else None, **evidence)


def probe_engine_context() -> dict:
    """Read-only SDK authentication/context preflight; never records a turn."""
    missing = need_env(("AGENT_ENGINE_URL", "AGENT_ENGINE_PROJECT_ID",
                        "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"))
    if missing:
        return result("engine-context.live", "blocked", "Required configuration missing", missing=missing)
    if os.environ["AGENT_ENGINE_URL"].rstrip("/") != "https://agentengine.mongodb.com":
        return result("engine-context.live", "blocked", "This probe targets the official hosted service only")
    from agent_engine_sdk_memory import Memory, MemoryRequestContext

    with Memory(base_url=os.environ["AGENT_ENGINE_URL"],
                project_id=os.environ["AGENT_ENGINE_PROJECT_ID"],
                service_account_token=os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]) as memory:
        chat = memory.bind(MemoryRequestContext(user_id="phase0-readonly-diagnostic",
                                              session_id="phase0-readonly-diagnostic"))
        chat.build_context(query="Synthetic connectivity check", enabled_sources={"stm"}, max_tokens=128)
    return result("engine-context.live", "pass", "Read-only context request succeeded; no write, isolation or attachment proof")


def assess_engine_auth(statuses: dict) -> dict:
    """Require a live positive control and explicit authentication denials."""
    expected = {"valid": 200, "missing": 401, "invalid": 401, "different_project": 403}
    passed = all(statuses.get(name) == status for name, status in expected.items())
    return result("engine-auth.live", "pass" if passed else "fail",
                  "Read-only credential and synthetic project-mismatch checks; not real cross-project "
                  "or application-tenant authorization, and not least-privilege proof",
                  http_statuses=statuses, different_project_is_synthetic=True, new_writes=0)


def probe_engine_auth() -> dict:
    missing = need_env(("AGENT_ENGINE_URL", "AGENT_ENGINE_PROJECT_ID",
                        "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"))
    if missing:
        return result("engine-auth.live", "blocked", "Required configuration missing", missing=missing)
    if os.environ["AGENT_ENGINE_URL"].rstrip("/") != "https://agentengine.mongodb.com":
        return result("engine-auth.live", "blocked", "This probe targets the official hosted service only")
    import secrets
    import httpx
    from urllib.parse import quote

    project = os.environ["AGENT_ENGINE_PROJECT_ID"]
    foreign = secrets.token_hex(12)
    if foreign == project:
        return result("engine-auth.live", "blocked", "Synthetic project ID collision")
    token = os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]
    cases = (("valid", project, token), ("missing", project, None),
             ("invalid", project, "synthetic-invalid-token"), ("different_project", foreign, token))
    body = {"query": "Synthetic authentication boundary check",
            "user_id": "phase0-readonly-diagnostic", "session_id": "phase0-readonly-diagnostic",
            "enabled_sources": ["stm"], "max_tokens": 2048}
    statuses = {}
    # Four sequential reads, no retries or redirects. Timeout applies per I/O,
    # not to the total diagnostic duration. Never retain response bodies.
    with httpx.Client(base_url="https://agentengine.mongodb.com", timeout=20,
                      follow_redirects=False) as client:
        for name, target, credential in cases:
            response = client.post(
                "/api/v1/projects/" + quote(target, safe="") + "/memory/context",
                headers={"Authorization": "Bearer " + credential} if credential else {}, json=body,
            )
            statuses[name] = response.status_code
    return assess_engine_auth(statuses)


def probe_engine() -> dict:
    """Write a synthetic STM turn and check session/user separation, not tenant ACLs."""
    missing = need_env(("AGENT_ENGINE_URL", "AGENT_ENGINE_PROJECT_ID",
                        "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"))
    if missing:
        return result("engine.live", "blocked", "Required configuration missing", missing=missing)
    if os.environ["AGENT_ENGINE_URL"].rstrip("/") != "https://agentengine.mongodb.com":
        return result("engine.live", "blocked", "This probe targets the official hosted service only")
    from uuid import uuid4
    from agent_engine_sdk_memory import Memory, MemoryRequestContext

    run_id = uuid4().hex
    marker = "SYNTHETIC-PROBE-" + run_id
    stage = "initialize_client"
    write_outcome = "not_attempted"
    try:
        with Memory(base_url=os.environ["AGENT_ENGINE_URL"],
                    project_id=os.environ["AGENT_ENGINE_PROJECT_ID"],
                    service_account_token=os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]) as memory:
            chat = memory.bind(MemoryRequestContext(user_id="phase0-user-" + run_id,
                                                  session_id="phase0-session-" + run_id))
            stage = "record_turn"
            write_outcome = "unknown"
            written = chat.record_turn(role="user", content="My synthetic verification marker is " + marker,
                             idempotency_key="phase0-turn-" + run_id)
            if written.acknowledged is not True:
                return result("engine.live", "fail", "SDK returned without acknowledging the write",
                              failed_stage=stage, write_outcome="not_acknowledged",
                              synthetic_run_id=run_id)
            write_outcome = "acknowledged"
            stage = "same_session_context"
            # SDK 0.11.11 reserves 500 tokens before selecting whole memory chunks.
            own = chat.build_context(query="What is my synthetic verification marker?",
                                     enabled_sources={"stm"}, max_tokens=2048)
            stage = "other_session_context"
            other = memory.bind(MemoryRequestContext(user_id="phase0-other-" + run_id,
                                                   session_id="phase0-other-session-" + run_id))
            unrelated = other.build_context(query="What is my synthetic verification marker?",
                                            enabled_sources={"stm"}, max_tokens=2048)
            stage = "close_client"
    except Exception as exc:
        return probe_failure("engine", exc, failed_stage=stage,
                             write_outcome=write_outcome, synthetic_run_id=run_id)
    found = marker in json.dumps(own.formatted_context)
    absent = marker not in json.dumps(unrelated.formatted_context)
    return result("engine.live", "pass" if found and absent else "fail",
                  "Synthetic STM write/read and distinct user/session check only; not tenant authorization, "
                  "same-cluster attachment, durable extraction, or hosted agent execution proof",
                  same_session_marker_found=found, other_session_marker_absent=absent,
                  write_outcome=write_outcome, synthetic_run_id=run_id)


def probe_voyage() -> dict:
    if need_env(("VOYAGE_API_KEY",)):
        return result("voyage.live", "blocked", "VOYAGE_API_KEY missing")
    from compatibility.voyage_http import VoyageHTTPProbe
    client = VoyageHTTPProbe(os.environ["VOYAGE_API_KEY"],
                            base_url=os.environ.get("VOYAGE_BASE_URL", "https://api.voyageai.com/v1"))
    text = ("Synthetic telecom procedure: verify the router power and regional outage status. "
            "Record the indicator state and open a support ticket if service remains unavailable. ") * 40
    chunks = client.contextual([text], documents=True)
    query = client.contextual(["How do I investigate an unavailable broadband connection?"], documents=False)
    ranked = client.rerank("How do I investigate broadband service?", [
        "Check the router power and regional outage status.",
        "A mobile plan invoice is payable next month.",
    ])
    return result("voyage.live", "pass", "Three real HTTP contract calls; not a retrieval quality evaluation",
                  contextual_dimension=256, chunk_count=len(chunks["data"][0]["data"]),
                  chunker_version_present=isinstance(chunks.get("chunker_version"), str),
                  query_count=len(query["data"]), rerank_count=len(ranked["data"]),
                  models=["voyage-context-4", "rerank-3"])


def build_report(probe: str, allow_live: bool, target: str = TARGET) -> dict:
    if probe == "offline":
        checks = [result("python.runtime", "pass" if platform.python_version() == target else "blocked",
                         "Exact planned interpreter required for runtime proof",
                         observed=platform.python_version(), target=target)]
        checks += metadata_checks(target) + import_checks()
        checks += [result(name, "blocked", "Not demonstrated by offline inspection") for name in (
            "uv.frozen_install_build", "mongodb.search_autoembed_fusion_isolation",
            "voyage.contextual_chunking_rerank", "docling.pdf_ocr_alignment",
            "voice.round_trip_session", "engine.memory_single_cluster", "engine.hosted_audit_replay",
        )]
    else:
        checks = [run_live(probe, allow_live)]
    return {"recorded_at": datetime.now(timezone.utc).isoformat(),
            "scope": probe, "phase0_complete": False,
            "note": "Individual probes are evidence only; phase acceptance also requires the documented live gates.",
            "environment": {"python": platform.python_version(), "system": platform.system(),
                            "machine": platform.machine()},
            "configuration_presence": {name: bool(os.environ.get(name, "").strip()) for name in ENV_NAMES},
            "checks": checks}


def exit_code(report: dict) -> int:
    statuses = {item["status"] for item in report["checks"]}
    return 1 if "fail" in statuses else (2 if "blocked" in statuses else 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", choices=("offline", "mongodb", "openai", "voyage", "engine", "engine-context", "engine-auth"), default="offline")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--target-python", default=TARGET)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.probe, args.allow_live, args.target_python)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
