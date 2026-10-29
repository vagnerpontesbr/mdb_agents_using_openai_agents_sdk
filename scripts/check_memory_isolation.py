"""Read-only user/session and durable-memory checks for an existing synthetic turn.

This checks filters under one service credential, not tenant authorization.
No writes, promotion requests, configuration changes or polling are performed.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_compatibility import need_env, probe_failure


def assess(observations):
    """Negative controls require their matching positive control to pass."""
    checks = []
    for name, expected, positive in (
        ("stm_positive", True, None),
        ("stm_other_session", False, "stm_positive"),
        ("stm_other_user", False, "stm_positive"),
        ("durable_new_session", True, None),
        ("durable_other_user", False, "durable_new_session"),
    ):
        observation = observations.get(name, {})
        status = "pass" if (observation.get("healthy") is True
                            and observation.get("marker_found") is expected) else "fail"
        # A leak remains a failure even if the positive control also failed.
        if positive and observation.get("marker_found") is not True:
            control = observations.get(positive, {})
            if control.get("healthy") is not True or control.get("marker_found") is not True:
                status = "blocked"
        checks.append({"check": name, **observation, "status": status})
    return checks


def probe(run_id):
    from agent_engine_sdk_memory import Memory, SourceSpec

    user, session = "phase0-user-" + run_id, "phase0-session-" + run_id
    marker = "SYNTHETIC-PROBE-" + run_id
    cases = (
        ("stm_positive", user, session, ("stm",)),
        ("stm_other_session", user, "phase0-new-session-" + run_id, ("stm",)),
        ("stm_other_user", "phase0-other-" + run_id, session, ("stm",)),
        ("durable_new_session", user, "phase0-new-session-" + run_id, ("semantic", "episodic")),
        ("durable_other_user", "phase0-other-" + run_id, "phase0-new-session-" + run_id,
         ("semantic", "episodic")),
    )
    observations = {}
    with Memory(base_url=os.environ["AGENT_ENGINE_URL"],
                project_id=os.environ["AGENT_ENGINE_PROJECT_ID"],
                service_account_token=os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]) as memory:
        for name, uid, sid, sources in cases:
            try:
                response = memory.build_context_from_sources(
                    query="What is my synthetic verification marker?",
                    sources=[SourceSpec(source=s, mode="hybrid", top_k=3) for s in sources],
                    user_id=uid, session_id=sid, max_tokens=2048,
                )
                outcomes = [{k: v for k, v in item.items() if k in (
                    "source", "requested_mode", "effective_mode", "count", "retryable"
                )} | {"error_present": bool(item.get("error"))}
                    for item in response.metadata.source_outcomes or []]
                healthy = (len(outcomes) == len(sources)
                           and {o.get("source") for o in outcomes} == set(sources)
                           and all(not o["error_present"] and not o.get("retryable", False)
                                   and o.get("effective_mode") == "hybrid" for o in outcomes))
                observations[name] = {"healthy": healthy,
                                      "marker_found": marker in json.dumps(response.formatted_context),
                                      "source_outcomes": outcomes}
            except Exception as exc:
                failure = probe_failure(name, exc)
                observations[name] = {k: v for k, v in failure.items() if k not in ("check", "status")}
                observations[name]["healthy"] = False
    return assess(observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Synthetic run ID from the existing engine probe")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.run_id):
        parser.error("run-id must be a synthetic 32-character lowercase hexadecimal ID")
    missing = need_env(("AGENT_ENGINE_URL", "AGENT_ENGINE_PROJECT_ID", "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"))
    if not args.allow_live or missing or os.environ.get("AGENT_ENGINE_URL", "").rstrip("/") != "https://agentengine.mongodb.com":
        checks = [{"check": "prerequisites", "status": "blocked",
                   "detail": "Requires --allow-live, hosted Engine URL and configured credentials", "missing": missing}]
    else:
        try:
            checks = probe(args.run_id)
        except Exception as exc:
            checks = [probe_failure("memory-isolation", exc)]
    report = {"recorded_at": datetime.now(timezone.utc).isoformat(), "synthetic_run_id": args.run_id,
              "new_writes": 0, "phase0_complete": False,
              "scope": "User/session filters and exact durable marker retrieval; not tenant authorization",
              "checks": checks}
    encoded = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded)
    print(encoded, end="")
    return 1 if any(c["status"] == "fail" for c in checks) else (2 if any(c["status"] == "blocked" for c in checks) else 0)


if __name__ == "__main__":
    raise SystemExit(main())
