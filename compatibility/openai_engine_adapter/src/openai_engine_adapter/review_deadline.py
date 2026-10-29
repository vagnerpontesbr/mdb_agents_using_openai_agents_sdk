"""Backend review validity; deadline persistence/replay remains Engine-owned."""

import time
from pydantic import BaseModel, ConfigDict, Field, model_validator
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ACTIVITY_KIND_TOOL
from agent_engine_runner_shared.workflow import run_serial_activity

from .adapter import UnsupportedContract
from .managed_memory import acknowledge_control


class ReviewDeadline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    issued_at: float = Field(gt=0)
    expires_at: float = Field(gt=0)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.expires_at <= self.issued_at:
            raise ValueError("Review deadline must follow issue time")
        return self

    def expired(self):
        return time.time() >= self.expires_at


def record_deadline(*, client, context, action, ttl_seconds, ordinal):
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600:
        raise UnsupportedContract("Synthetic review TTL must be between 1 and 3600 seconds")

    def issue(_):
        now = time.time()
        return ReviewDeadline(issued_at=now, expires_at=now + ttl_seconds).model_dump()

    recorded = run_serial_activity(
        client=client, kind=ACTIVITY_KIND_TOOL, name="openai_engine_review_deadline",
        activity_ordinal=ordinal,
        semantic_input={"contract": "openai-engine-review-v2", "requesting_user_id": context.user_id,
                        "action": action.model_dump(mode="json"), "ttl_seconds": ttl_seconds},
        execute=issue, on_unknown_outcome="fail", on_activity_resolved=acknowledge_control,
    )
    return ReviewDeadline.model_validate(recorded, strict=True)
