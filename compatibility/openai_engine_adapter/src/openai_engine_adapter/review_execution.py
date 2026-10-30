"""Opt-in AER review stream. Requires a real Engine durable attempt.

Not enabled by invoice:app. Read flow replay remains Engine-owned; this bridge
has no checkpoint database or client-supplied SDK RunState.
"""

import asyncio
import json

from agent_engine_sdk.models import StreamEvent
from agent_engine_runner_shared.context import get_current_oe_url
from agent_engine_runner_shared.generated.workflow.v1.state_pb2 import StateSnapshot
from agent_engine_runner_shared.workflow import (
    WorkflowClient, AsyncWorkflowClient, current_attempt_context,
    finalize_current_step_suspensions_command,
    allocate_activity_ordinal, settle_execution,
)
from agent_engine_runner_shared.workflow.protojson import json_to_proto_struct

from .adapter import UnsupportedContract
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import (
    ActivitySuspension, ActivityContext, StepSuspensionEntry, ACTIVITY_OUTCOME_KIND_SUSPENDED,
)
from agent_engine_runner_shared.workflow.context import (
    current_step_ordinal, interrupted_activities, mark_interrupted_activities_answered,
)
from agent_engine_runner_shared.workflow.activity import unwrap_activity_outcome

from .review import request_review, ReviewInterrupt, ReviewDecision, recorded_review_decision
from .review_deadline import record_deadline
from .managed_memory import acknowledge_control


async def finalize_review_interrupt(attempt, interrupt):
    """Translate the single native pause using Engine 0.11.11 finalization."""
    pending = interrupted_activities(current_step_ordinal())
    if len(pending) != 1 or pending[0].control_flow is not interrupt:
        raise UnsupportedContract("Review must own exactly one pending interruption")
    command = pending[0].command
    suspension = StepSuspensionEntry(
        position=command.position, activity_kind=command.activity_kind,
        activity_name=command.activity_name, semantic_input=command.semantic_input,
        suspension=ActivitySuspension(reason="agent_interrupt",
            context=json_to_proto_struct({"value": interrupt.value})),
    )
    async with AsyncWorkflowClient(get_current_oe_url()) as client:
        entries = await client.finalize_step(
            finalize_current_step_suspensions_command(attempt, [suspension]))
    if len(entries) != 1 or entries[0].position != command.position:
        raise UnsupportedContract("Engine returned an unexpected review frontier")
    outcome = entries[0].outcome
    if outcome.outcome_kind == ACTIVITY_OUTCOME_KIND_SUSPENDED:
        if not outcome.activity_id:
            raise UnsupportedContract("Engine returned an empty review activity ID")
        return StreamEvent(event="suspend", data={
            "suspend_payload": interrupt.value,
            "interrupts": [{"id": outcome.activity_id, "value": interrupt.value}],
            "resume_schema": {
                "type": "object", "required": ["resume_map"],
                "properties": {"resume_map": {
                    "type": "object", "required": [outcome.activity_id],
                    "properties": {outcome.activity_id: ReviewDecision.model_json_schema()},
                    "additionalProperties": False,
                }}, "additionalProperties": True,
            }, "metadata": {},
        })
    decision = recorded_review_decision(unwrap_activity_outcome(outcome))
    # Resolved-at-finalization skips the activity helper's normal replay hook.
    with WorkflowClient(get_current_oe_url()) as client:
        acknowledge_control(client, ActivityContext(
            workflow_identity=outcome.workflow_identity, activity_id=outcome.activity_id,
            attempt_id=outcome.attempt_id, fencing_token=outcome.fencing_token,
        ), decision)
    mark_interrupted_activities_answered([command.position])
    return decision


class ReviewExecutionAgent:
    """Review release of a bounded read result, with a server-owned action factory.

    The wrapped agent must be the Engine-proxied single-read adapter. The
    factory must describe the exact proposed action from that validated result.
    This is not suitable for writes before the review point.
    """

    def __init__(self, read_agent, action_factory, *, ttl_seconds=None):
        self.read_agent = read_agent
        self.action_factory = action_factory
        self.ttl_seconds = ttl_seconds

    def execute(self, ctx, input):
        return self._stream(ctx.model_copy(deep=True), input.model_copy(deep=True))

    async def _stream(self, ctx, input):
        attempt = current_attempt_context()
        if attempt is None or not get_current_oe_url():
            raise UnsupportedContract("Review execution requires an Engine durable attempt and callback URL")
        identity = attempt.workflow_identity
        if ((ctx.execution_id, ctx.session_id, ctx.workspace_id)
                != (identity.execution_id, identity.session_id, identity.tenant_scope.workspace_id)
                or not ctx.user_id or not attempt.attempt_id or not attempt.fencing_token
                or not identity.tenant_scope.org_id or not identity.tenant_scope.project_id):
            raise UnsupportedContract("Review execution identity does not match Engine attempt")
        if ctx.metadata or ctx.previous_execution_cancelled:
            raise UnsupportedContract("Opaque checkpoints and cancellation recovery are unsupported")
        if ctx.resume and (not attempt.replay_mode or not isinstance(ctx.resume_data, dict)):
            raise UnsupportedContract("Review resume requires an Engine replay attempt and resume map")
        if not ctx.resume and ctx.resume_data is not None:
            raise UnsupportedContract("Unsolicited resume data is unsupported")
        # Replay intentionally re-enters the same bounded read flow; its real
        # Engine proxies resolve prior activities. No decision is read here.
        fresh_ctx = ctx.model_copy(update={"resume": False, "resume_data": None})
        output = await self.read_agent.execute(fresh_ctx, input)
        result = output.response["output"]
        action = self.action_factory(result)
        deadline = None
        if self.ttl_seconds is not None:
            deadline_ordinal = allocate_activity_ordinal("review-deadline:" + action.tool_call_id)
            def load_deadline():
                with WorkflowClient(get_current_oe_url()) as client:
                    return record_deadline(client=client, context=ctx, action=action,
                                           ttl_seconds=self.ttl_seconds, ordinal=deadline_ordinal)
            deadline = await asyncio.to_thread(load_deadline)
        ordinal = allocate_activity_ordinal("review:" + action.tool_call_id)

        def review():
            with WorkflowClient(get_current_oe_url()) as client:
                return request_review(client=client, context=ctx, action=action, activity_ordinal=ordinal, deadline=deadline)

        try:
            decision = await asyncio.to_thread(review)
        except ReviewInterrupt as interrupt:
            decision = await finalize_review_interrupt(attempt, interrupt)
            if isinstance(decision, StreamEvent):
                yield decision
                return
        status = "rejected" if decision.decision == "reject" else (
            "expired" if deadline is not None and deadline.expired() else "approved")
        response = result if status == "approved" else json.dumps(
            {"status": status, "tool_call_id": action.tool_call_id}, separators=(",", ":"),
        )
        snapshot = StateSnapshot(properties=json_to_proto_struct({
            "adapter_contract": "openai-engine-review-v2" if deadline is not None else "openai-engine-review-v1",
            "response": response,
        }))
        # A result is visible only after OE accepts both step and completion.
        await settle_execution(attempt, snapshot)
        yield StreamEvent(event="result", data={"response": response})
