"""Inspect the pinned Engine/OpenAI contract offline; never start a runtime.

Exit 2 means native hosted integration remains blocked, even when inspection
checks pass. This does not implement or accept a custom adapter.
"""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
from types import SimpleNamespace


def inspect_contract():
    from agents import Agent
    from agent_engine_sdk import BaseApp
    from agent_engine_sdk.interfaces import BaseAgent
    from agent_engine_runner_shared import hooks
    from agent_engine_runner_shared.runtime import TenantRuntime

    versions = {name: version(name) for name in (
        "openai-agents", "agent-engine-sdk", "agent-engine-runner-shared",
    )}
    expected = {"openai-agents": "0.24.0", "agent-engine-sdk": "0.11.11",
                "agent-engine-runner-shared": "0.11.11"}
    if versions != expected or platform.python_version() != "3.15.2":
        raise ValueError("Run in the frozen hosted-runtime diagnostic environment")
    agent = Agent(name="OfflineContractProbe", instructions="Synthetic contract inspection only.")
    # Exercise the actual package dispatch guard with only the state it reads.
    # Never construct TenantRuntime: its constructor wires tracing and memory.
    rejected = False
    try:
        TenantRuntime.get_agent(SimpleNamespace(_graph_builder=agent))
    except RuntimeError as exc:
        rejected = str(exc) == (
            "Graph builder must be a BaseApp instance with get_agent(). "
            "Plain callables are not supported."
        )
    missing_llm_factory = False
    try:
        hooks.get_llm_adapter_factory()
    except RuntimeError:
        missing_llm_factory = True
    checks = {
        "native_agent_is_engine_base_agent": isinstance(agent, BaseAgent),
        "native_agent_has_get_agent": callable(getattr(agent, "get_agent", None)),
        "native_agent_has_run_entrypoint": callable(getattr(agent, "run", None)),
        "runner_rejected_native_agent_with_expected_guard": rejected,
        "llm_adapter_factory_missing": missing_llm_factory,
        "workflow_adapter_registered": hooks.get_workflow_adapter() is not None,
        "suspend_handler_registered": hooks.get_suspend_handler() is not None,
        "durable_activity_suspend_handler_registered": hooks.get_durable_activity_suspend_handler() is not None,
    }
    expected_checks = {
        "native_agent_is_engine_base_agent": False,
        "native_agent_has_get_agent": False,
        "native_agent_has_run_entrypoint": False,
        "runner_rejected_native_agent_with_expected_guard": True,
        "llm_adapter_factory_missing": True,
        "workflow_adapter_registered": False,
        "suspend_handler_registered": False,
        "durable_activity_suspend_handler_registered": False,
    }
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "system": platform.system(),
                        "machine": platform.machine(), "packages": versions},
        "inspection_status": "pass" if checks == expected_checks else "fail",
        "native_hosted_integration": "blocked",
        "phase0_complete": False,
        "scope": "Installed-package contract inspection, not adapter or hosted execution acceptance",
        "checks": checks,
        "base_app_abstract_methods": sorted(BaseApp.__abstractmethods__),
        "network_calls": 0,
        "runtime_started": False,
        "limitations": [
            "The dispatch guard was called with synthetic state, without constructing the runtime.",
            "No custom adapter was registered; missing hooks describe this environment only.",
            "Generic interfaces may allow a custom adapter, whose support and behavior remain untested.",
            "No model calls, tools, audit, replay, approval/resume, Linux or hosted build were tested.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = inspect_contract()
    except Exception as exc:
        report = {"inspection_status": "fail", "error_class": type(exc).__name__,
                  "native_hosted_integration": "unverified", "phase0_complete": False}
    encoded = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded)
    print(encoded, end="")
    return 2 if report["inspection_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
