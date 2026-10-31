"""Read Engine accounting without mistaking unpriced calls for zero billed cost."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from telecom_app.journey import WORKSPACE, EngineAPI

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "budget_usd": 30,
        "billed_total_usd": None,
        "status": "billing_unreconciled",
        "openai_admin_key_configured": any(
            os.getenv(k) for k in ("OPENAI_ADMIN_KEY", "OPENAI_ADMIN_API_KEY")
        ),
        "sources": [
            "https://www.mongodb.com/docs/api/doc/agentengine",
            "https://developers.openai.com/api/docs/pricing",
            "https://developers.openai.com/cookbook/examples/completions_usage_api",
        ],
        "limitations": [
            "Engine dashboard is workspace-scoped over seven days, not Phase 8-only",
            "Unpriced calls and unobserved managed memory/gateway usage prevent billing reconciliation",
            "OpenAI organization Usage/Costs API requires an Admin Key",
            "Known token estimate is not an invoice or upper bound for all provider consumption",
            "No additional provider load should run until missing billing is reconciled",
        ],
    }
    with args.output.open("x") as output:
        try:
            data = EngineAPI().call("cost/dashboard?period=7d&workspace_id=" + WORKSPACE)
            report["engine_dashboard"] = {
                k: data.get(k) for k in ("summary", "by_model", "daily_trend")
            }
        except Exception as error:
            report["dashboard_error_type"] = type(error).__name__
        traces = json.loads((ROOT / "compatibility/phase8-engine-trace-metrics.json").read_text())
        inputs = sum(r["tokens"]["input"] for r in traces["rows"])
        outputs = sum(r["tokens"]["output"] for r in traces["rows"])
        report["known_native_model_estimate"] = {
            "model": "gpt-5.6-luna",
            "input_tokens": inputs,
            "output_tokens": outputs,
            "input_usd_per_million": 0.20,
            "output_usd_per_million": 1.20,
            "uncached_standard_estimate_usd": round((inputs * 0.20 + outputs * 1.20) / 1e6, 8),
            "scope": "15 observed session-correlated model calls only",
        }
        voice = json.loads((ROOT / "compatibility/phase8-voice-contention.json").read_text())
        report["voice"] = {
            "attempts": voice["provider_attempts"],
            "billed_usd": None,
            "tts_output_seconds": voice["baseline"]["audio_seconds"]
            + voice["contention"]["tts"]["audio_seconds"],
            "stt_input_seconds": voice["baseline"]["audio_seconds"],
        }
        json.dump(report, output, indent=2)
        output.write("\n")
    print(json.dumps({"status": report["status"], "billed_total_usd": None}))


if __name__ == "__main__":
    main()
