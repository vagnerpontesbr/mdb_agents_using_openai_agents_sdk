"""Authenticated native Engine review for exact document metadata; no local wait store."""

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from compatibility.demo_auth.auth import AccessDenied

from .identity import IdentityService
from .journey import EngineAPI, JourneyConflict, JourneyService, session_id
from .knowledge import Version

PREFIX = "__telecom_document_review__:"


def request_data(job_id: str, version: Version) -> dict[str, Any]:
    return {"job_id": job_id, "metadata": version.model_dump(mode="json")}


def request_digest(request: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class NativePublicationApproval:
    execution_id: str
    requester: str
    request_digest: str
    expires_at: float


class DocumentReview:
    def __init__(self, identity: IdentityService, engine: EngineAPI) -> None:
        self.identity, self.engine = identity, engine
        self.journey = JourneyService(identity, engine)

    def create(self, token: str, job_id: str, version: Version) -> dict[str, Any]:
        actor = self.identity.principal(token)
        if actor.role != "admin":
            raise AccessDenied("Administrator required")
        message = PREFIX + json.dumps(request_data(job_id, version), separators=(",", ":"))
        if len(message) > 4000:
            raise ValueError("Metadata exceeds the native review bound")
        session = session_id(actor.user_id, uuid4())
        result = self.engine.invoke(actor.user_id, session, message)
        execution = str(UUID(result["execution_id"]))
        state = self.journey.execution(token, execution)
        if state["session_id"] != session:
            raise JourneyConflict("Publication session mismatch")
        return self.present(token, execution)

    def present(self, token: str, execution_id: str) -> dict[str, Any]:
        execution = self.journey.execution(token, execution_id)
        status = execution["status"]
        if status == "suspended":
            interrupts = execution.get("suspend_context", {}).get("interrupts", [])
            if len(interrupts) != 1:
                raise JourneyConflict("Unexpected publication review frontier")
            review = interrupts[0].get("value", {})
            action = review.get("action", {})
            generation = execution.get("suspend_generation")
            if (
                review.get("contract") != "openai-engine-review-v2"
                or review.get("requesting_user_id") != execution["user_id"]
                or review.get("allowed_decisions") != ["approve", "reject"]
                or action.get("tool_name") != "telco_publish_knowledge"
                or action.get("tool_call_id") != "document-publication"
                or type(generation) is not int
                or generation < 1
            ):
                raise JourneyConflict("Unexpected publication review contract")
            request = action["arguments"]
            self.validate_request(request)
            digest = request_digest(
                {
                    "execution_id": execution_id,
                    "review": review,
                    "generation": generation,
                    "requester": execution["user_id"],
                }
            )
            return {
                "execution_id": execution_id,
                "status": status,
                "request": request,
                "action_digest": digest,
                "generation": generation,
            }
        if status == "completed":
            raw = execution.get("result")
            if isinstance(raw, dict) and set(raw) == {"response"}:
                raw = raw["response"]
            result = json.loads(raw) if isinstance(raw, str) else raw
            if (
                not isinstance(result, dict)
                or result.get("contract") != "telecom-document-review-v1"
                or result.get("requester") != execution["user_id"]
                or result.get("status") not in ("approved", "rejected", "expired")
            ):
                raise JourneyConflict("Unexpected publication outcome")
            self.validate_request(result["request"])
            if result.get("request_digest") != request_digest(result["request"]):
                raise JourneyConflict("Publication digest mismatch")
            return {"execution_id": execution_id, "status": status, "result": result}
        if status not in ("pending", "running", "resuming", "error", "cancelled"):
            raise JourneyConflict("Unexpected execution status")
        return {"execution_id": execution_id, "status": status}

    @staticmethod
    def validate_request(request: Any) -> None:
        if not isinstance(request, dict) or set(request) != {"job_id", "metadata"}:
            raise JourneyConflict("Invalid publication request")
        job = request["job_id"]
        if (
            not isinstance(job, str)
            or len(job) != 64
            or any(c not in "abcdef0123456789" for c in job)
        ):
            raise JourneyConflict("Invalid publication job")
        Version.model_validate(request["metadata"])

    def decide(self, token: str, execution_id: str, digest: str, decision: str) -> dict[str, Any]:
        if decision not in ("approve", "reject"):
            raise ValueError("Invalid publication decision")
        pending = self.present(token, execution_id)
        if pending["status"] != "suspended" or pending.get("action_digest") != digest:
            raise JourneyConflict("Publication review changed")
        self.journey.execution(token, execution_id)
        self.engine.resume(execution_id, pending["generation"], decision)
        return self.present(token, execution_id)

    def verified(
        self, token: str, execution_id: str, job_id: str, version: Version
    ) -> NativePublicationApproval:
        state = self.present(token, execution_id)
        if state["status"] != "completed":
            raise JourneyConflict("Native approval is incomplete")
        result = state["result"]
        expires = result.get("expires_at")
        if (
            result["status"] != "approved"
            or result["request"] != request_data(job_id, version)
            or type(expires) not in (int, float)
            or not math.isfinite(expires)
            or not time.time() < expires
        ):
            raise JourneyConflict("Native approval does not authorize this publication")
        return NativePublicationApproval(
            execution_id, result["requester"], result["request_digest"], expires
        )
