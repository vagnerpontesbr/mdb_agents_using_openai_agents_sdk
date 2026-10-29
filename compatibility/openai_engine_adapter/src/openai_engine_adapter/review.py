"""Experimental Engine-owned review activity; not registered in the hosted app.

The caller must already be inside an OE-issued durable attempt. AER suspension
finalization and resume routing are separate, still-unvalidated integration
requirements. This module stores no checkpoint and accepts no caller decision.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from agent_engine_sdk.models import RequestContext
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ACTIVITY_KIND_TOOL
from agent_engine_runner_shared.workflow import (
    DurableActivityInterrupted, current_attempt_context, run_serial_activity,
)

from .adapter import UnsupportedContract
from .managed_memory import acknowledge_control


class ReviewInterrupt(Exception):
    """Adapter-native control flow; only OE finalization can publish a wait."""

    def __init__(self, value):
        super().__init__("Review requires an Engine-owned answer")
        self.value = value


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tool_name: str = Field(min_length=1, max_length=128)
    tool_call_id: str = Field(min_length=1, max_length=256)
    arguments: dict[str, JsonValue]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Literal["approve", "reject"]


def request_review(*, client, context: RequestContext, action: ReviewAction,
                   activity_ordinal: int, deadline=None) -> ReviewDecision:
    """Record a wait, or consume OE's recorded answer at the same position.

    A returned decision does not authorize a business write: the caller must
    still enforce current eligibility, expiry and idempotency. Reviewer
    authentication and resolution of the activity belong to Engine.
    """
    attempt = current_attempt_context()
    if attempt is None:
        raise UnsupportedContract("Review requires an Engine-owned durable attempt")
    identity = attempt.workflow_identity
    scope = identity.tenant_scope
    if (not attempt.attempt_id or not attempt.fencing_token
            or not scope.org_id or not scope.project_id
            or not all((context.execution_id, context.session_id, context.workspace_id, context.user_id))
            or (identity.execution_id, identity.session_id, scope.workspace_id)
            != (context.execution_id, context.session_id, context.workspace_id)):
        raise UnsupportedContract("Review context does not match the Engine attempt")
    if type(activity_ordinal) is not int or activity_ordinal < 1:
        raise UnsupportedContract("Review requires a stable positive activity ordinal")
    # Copy nested arguments: frozen Pydantic fields alone do not freeze dicts.
    action_data = ReviewAction.model_validate(action.model_dump(), strict=True).model_dump(mode="json")
    semantic_input = {
        "contract": "openai-engine-review-v1",
        "requesting_user_id": context.user_id,
        "action": action_data,
    }

    if deadline is not None:
        semantic_input["contract"] = "openai-engine-review-v2"
        semantic_input["deadline"] = deadline.model_dump()

    def suspend(_activity_context):
        raise DurableActivityInterrupted(ReviewInterrupt({
            **semantic_input, "allowed_decisions": ["approve", "reject"],
        }))

    answer = run_serial_activity(
        client=client, kind=ACTIVITY_KIND_TOOL, name="openai_engine_review",
        activity_ordinal=activity_ordinal, semantic_input=semantic_input,
        execute=suspend, on_unknown_outcome="fail", on_activity_resolved=acknowledge_control,
    )
    return ReviewDecision.model_validate(answer, strict=True)
