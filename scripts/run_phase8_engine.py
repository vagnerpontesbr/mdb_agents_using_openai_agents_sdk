"""Opt-in bounded native Engine concurrency probe with existing synthetic accounts.

At most six invoke attempts, concurrency two; no retries, billing mutations or
shared policy changes. Output excludes credentials, model prose and memory data.
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from run_phase5_evaluation import release_completed_runtime

from compatibility.demo_auth.auth import AccessDenied
from telecom_app.config import Settings
from telecom_app.database import connect, user_store
from telecom_app.identity import identity_service
from telecom_app.journey import EngineAPI, JourneyConflict, JourneyService, session_id

EXPECTED = "Your synthetic invoice total is USD 79.90, due on 2026-12-01."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--accounts-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live:
        print(
            json.dumps(
                {
                    "invoke_attempts": 0,
                    "planned_max_attempts": 6,
                    "max_concurrency": 2,
                    "approved_total_phase_budget_usd": 30,
                }
            )
        )
        return 0
    if not args.accounts_file:
        parser.error("--accounts-file is required for live probes")
    accounts = json.loads(args.accounts_file.read_text())
    if len(accounts) != 2:
        parser.error("Exactly two existing synthetic accounts are required")
    report = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "profile": "engine-concurrency-v1",
        "workflow_version": "8",
        "approved_total_phase_budget_usd": 30,
        "cost_usd": None,
        "stages": [],
        "invoke_attempts": 0,
        "limitations": [
            "Existing synthetic users; shared project-managed memory is not reset",
            "Engine preview has no charge per requester; upstream model usage remains billable",
            "Six invoke attempts only, not a capacity/soak or full cost-accounting result",
            "Current OpenAI direct and MongoDB gateway routes retained by requester",
            "No inferred provider charge from invocation count",
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
    with connect(Settings.from_env()) as client:
        identity = identity_service(user_store(client))
        tokens = []
        try:
            for account in accounts:
                token, actor = identity.login(
                    account["email"], account["password"], "phase8-native"
                )
                assert actor.user_id == account["user_id"]
                tokens.append(token)
            api = EngineAPI()
            service = JourneyService(identity, api)
            for name, count, same in (
                ("baseline", 1, False),
                ("distinct_sessions", 2, False),
                ("same_session", 2, True),
                ("post_concurrency", 1, False),
            ):
                stage = {"name": name, "attempts": []}
                report["stages"].append(stage)
                conversations = [uuid4() for _ in range(count)]
                if same:
                    conversations[1] = conversations[0]
                barrier = threading.Barrier(count)
                report["invoke_attempts"] += count
                assert report["invoke_attempts"] <= 6
                save()

                def invoke(index):
                    actor_index = 0 if same else index % 2
                    conversation = conversations[index]
                    row = {
                        "session_id": session_id(
                            accounts[actor_index]["user_id"], conversation
                        ),
                        "conversation_id": str(conversation),
                        "actor_index": actor_index,
                    }
                    barrier.wait(timeout=10)
                    started = time.monotonic()
                    try:
                        result = service.send(
                            tokens[actor_index], conversation, "Read my invoice demo-1."
                        )
                        row.update(status="completed", result=result)
                    except JourneyConflict:
                        row["status"] = "conflict"
                    except Exception as error:
                        row.update(status="uncertain", error_type=type(error).__name__)
                    row["seconds"] = round(time.monotonic() - started, 3)
                    return row

                with ThreadPoolExecutor(max_workers=count) as pool:
                    rows = list(pool.map(invoke, range(count)))
                for row in rows:
                    # Export identifiers and checks, not the user-facing model response.
                    stage["attempts"].append(
                        {key: value for key, value in row.items() if key != "result"}
                    )
                save()
                statuses = sorted(row["status"] for row in rows)
                assert statuses == (
                    ["completed", "conflict"] if same else ["completed"] * count
                )
                for row, exported in zip(rows, stage["attempts"], strict=True):
                    if row["status"] != "completed":
                        continue
                    result = row["result"]
                    index = row["actor_index"]
                    exported["execution_id"] = result["execution_id"]
                    save()
                    assert (
                        result["status"] == "completed" and result["text"] == EXPECTED
                    )
                    try:
                        service.present(tokens[1 - index], result["execution_id"])
                    except AccessDenied:
                        exported["other_user_denied"] = True
                    else:
                        raise AssertionError("Other user admitted")
                    exported["runtime_release"] = release_completed_runtime(
                        api, row["session_id"], result["execution_id"]
                    )
                    assert (
                        JourneyService(identity, EngineAPI()).latest(
                            tokens[index], conversations[rows.index(row)]
                        )
                        == result
                    )
                    exported["exact_result"] = True
                    exported["recovered_after_runtime_release"] = True
                    save()
                stage["status"] = "passed"
                save()
                print(
                    json.dumps({"stage": name, "status": stage["status"]}), flush=True
                )
            report["status"] = "passed"
        except Exception as error:
            report["status"] = "stopped"
            report["error_type"] = type(error).__name__
        finally:
            for token in tokens:
                identity.logout(token)
            save()
            output.close()
    print(
        json.dumps(
            {"status": report["status"], "invoke_attempts": report["invoke_attempts"]}
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
