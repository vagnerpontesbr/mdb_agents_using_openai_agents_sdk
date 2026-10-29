"""Opt-in OE negative-control fixture. Never used by the invoice entrypoints.

A harmless activity records a synthetic action and the owning lease in Engine.
Mutated starts must be rejected; a resumed attempt also tests the original lease.
No external business operation is dispatched and no local state is persisted.
"""

import asyncio
import json

from agent_engine_runner_shared.context import get_current_oe_url
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ACTIVITY_KIND_TOOL
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import (
    WORKFLOW_ERROR_CODE_NONDETERMINISTIC, WORKFLOW_ERROR_CODE_STALE_FENCE,
)
from agent_engine_runner_shared.workflow import (
    WorkflowClient, WorkflowClientError, allocate_activity_ordinal,
    current_attempt_context, run_serial_activity,
)
from agent_engine_runner_shared.workflow.activity import build_activity_command

from .adapter import UnsupportedContract
from .app import OpenAIEngineApp
from .review_execution import ReviewExecutionAgent
from .review_invoice import app as review_app


def probe_activity_contract(client, attempt, ordinal):
    """Exercise real OE rejection paths; unexpected acceptance is fatal."""
    semantic = {"contract": "synthetic-oe-controls-v1", "action": {
        "tool_name": "release_synthetic_invoice", "tool_call_id": "release-demo-1",
        "arguments": {"invoice_id": "demo-1", "amount_minor": 7990},
    }}
    options = dict(attempt=attempt, kind=ACTIVITY_KIND_TOOL,
                   name="synthetic_contract_control", activity_ordinal=ordinal,
                   semantic_input=semantic, on_unknown_outcome="fail")
    original = run_serial_activity(client=client, **options, execute=lambda context: {
        "attempt_id": context.attempt_id, "fencing_token": context.fencing_token,
    })
    original_fence = original["fencing_token"]
    if type(original_fence) not in (int, float) or not original_fence > 0 or int(original_fence) != original_fence:
        raise UnsupportedContract("Recorded probe fence is not a positive integer")
    original_fence = int(original_fence)
    command = build_activity_command(**options)
    results = {}

    def require_rejection(candidate, expected, label):
        try:
            client.start_activity(candidate)
        except WorkflowClientError as error:
            if error.code != expected:
                raise
            results[label] = "rejected"
        else:
            raise UnsupportedContract("Engine unexpectedly accepted " + label)

    for field, value in (("arguments", {"invoice_id": "demo-1", "amount_minor": 1}),
                         ("tool_call_id", "changed-call"), ("tool_name", "changed-tool")):
        changed = {**semantic, "action": {**semantic["action"], field: value}}
        require_rejection(build_activity_command(**{**options, "semantic_input": changed}),
                          WORKFLOW_ERROR_CODE_NONDETERMINISTIC, "changed_" + field)
    if attempt.replay_mode:
        if (original["attempt_id"] == attempt.attempt_id
                or not 0 < original_fence < attempt.fencing_token):
            raise UnsupportedContract("Probe resume did not acquire a newer Engine lease")
        stale = type(command)()
        stale.CopyFrom(command)
        stale.attempt_id = original["attempt_id"]
        stale.fencing_token = original_fence
        require_rejection(stale, WORKFLOW_ERROR_CODE_STALE_FENCE, "stale_attempt")
    else:
        results["stale_attempt"] = "awaiting_resume"
    return results


class ContractProbeAgent:
    def __init__(self, delegate):
        self.delegate = delegate

    def execute(self, ctx, input):
        return self._stream(ctx, input)

    async def _stream(self, ctx, input):
        attempt = current_attempt_context()
        if attempt is None or not get_current_oe_url():
            raise UnsupportedContract("Contract probe requires an Engine attempt")
        identity = attempt.workflow_identity
        if ((ctx.execution_id, ctx.session_id, ctx.workspace_id) !=
                (identity.execution_id, identity.session_id, identity.tenant_scope.workspace_id)
                or not ctx.user_id or ctx.metadata or ctx.previous_execution_cancelled
                or ctx.resume != attempt.replay_mode):
            raise UnsupportedContract("Contract probe context does not match Engine attempt")
        ordinal = allocate_activity_ordinal("synthetic-contract-control")

        def probe():
            with WorkflowClient(get_current_oe_url()) as client:
                return probe_activity_contract(client, attempt, ordinal)

        results = await asyncio.to_thread(probe)
        # Only fixed control labels and statuses are logged; no lease or user data.
        print("SYNTHETIC_OE_CONTRACT " + json.dumps(results, sort_keys=True), flush=True)
        async for event in self.delegate.execute(ctx, input):
            yield event


class ContractProbeApp(OpenAIEngineApp):
    def get_agent(self, callbacks=None, *, graph=None):
        delegate = super().get_agent(callbacks, graph=graph)
        if not isinstance(delegate, ReviewExecutionAgent):
            raise UnsupportedContract("Contract probe requires the review fixture")
        return ContractProbeAgent(delegate)


app = ContractProbeApp(
    name=review_app.name, instructions=review_app.instructions,
    llm_id=review_app.llm_id, model_name=review_app.model_name,
    provider_builder=review_app.provider_builder,
    provider_adapter_factory=review_app.provider_adapter_factory,
    review_action_factory=review_app.review_action_factory,
)
from .invoice import lookup_invoice
app.tool(contract=review_app.tools()[0])(lookup_invoice)
