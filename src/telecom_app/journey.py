"""Authenticated admission to native Engine execution; no application run store."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError
from urllib.request import Request, build_opener
from uuid import UUID

from pydantic import Field

from compatibility.demo_auth.auth import AccessDenied
from compatibility.demo_auth.engine import BASE, ORG, PROJECT, WORKSPACE, NoRedirect

from .contracts import Contract
from .identity import IdentityService
from .profile import Locale
from .turn_locale import Turn, execution_locale, validated_locale


class JourneyConflict(Exception):
    pass


class EngineUnavailable(Exception):
    pass


class ChatInput(Contract):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    audio_locale: Locale | None = None


class ExecutionInput(Contract):
    execution_id: UUID


class ConversationInput(Contract):
    conversation_id: UUID


class ReviewInput(ExecutionInput):
    action_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal["approve", "reject"]


class EngineAPI:
    def call(
        self, path: str, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            credential = json.loads((Path.home() / ".agentengine/auth.json").read_text())
            token = credential["credentials"][BASE]["access_token"]
            request = Request(
                BASE + f"/api/v1/projects/{PROJECT}/" + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    **(headers or {}),
                },
            )
            with build_opener(NoRedirect()).open(request, timeout=125) as response:
                body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise EngineUnavailable()
            result = json.loads(body)
            if not isinstance(result, dict) or result.get("success") is False:
                raise EngineUnavailable()
            return result
        except HTTPError as error:
            code = error.code
            error.close()
            if code == 409:
                raise JourneyConflict("Execution changed or a turn is already active") from None
            raise EngineUnavailable(
                "Engine unavailable; check the execution before retrying"
            ) from None
        except Exception:
            raise EngineUnavailable(
                "Engine unavailable; check the execution before retrying"
            ) from None

    def invoke(self, user: str, session: str, message: str) -> dict[str, Any]:
        return self.call(
            f"workspaces/{WORKSPACE}/invoke",
            {"user_id": user, "message": message},
            {"X-Session-ID": session, "X-Agent-Engine-Invoke-Timeout-Seconds": "120"},
        )

    def execution(self, execution: str) -> dict[str, Any]:
        result = self.call(f"executions/{execution}?workspace_id={WORKSPACE}")["execution"]
        if not isinstance(result, dict):
            raise EngineUnavailable()
        return result

    def resume(self, execution: str, generation: int, decision: str) -> dict[str, Any]:
        return self.call(
            f"executions/{execution}/resume?workspace_id={WORKSPACE}",
            {
                "decision": "approved" if decision == "approve" else "rejected",
                "suspend_generation": generation,
            },
        )

    def latest(self, session: str) -> str | None:
        data = self.call(f"sessions/{session}/runs?workspace_id={WORKSPACE}")
        runs = data.get("runs", [])
        if not isinstance(runs, list) or data.get("truncated") or len(runs) > 100:
            raise EngineUnavailable("Session history is outside the bounded demo")
        return str(runs[-1]["execution_id"]) if runs else None


def session_id(user: str, conversation: UUID) -> str:
    return "telco-" + hashlib.sha256(f"{user}|{conversation}".encode()).hexdigest()[:48]


class JourneyService:
    def __init__(self, identity: IdentityService, engine: EngineAPI,
                 *, localized_turns: bool = False) -> None:
        self.identity, self.engine = identity, engine
        self.localized_turns = localized_turns

    def turn_locale(self, token: str) -> Locale:
        self.identity.principal(token)
        if not self.localized_turns:
            return "en-US"
        return validated_locale(self.identity.profile(token)["locale"])

    def execution(self, token: str, execution_id: str) -> dict[str, Any]:
        user = self.identity.principal(token).user_id
        execution_id = str(UUID(execution_id))
        execution = self.engine.execution(execution_id)
        if (
            execution.get("user_id") != user
            or execution.get("execution_id") != execution_id
            or execution.get("org_id") != ORG
            or execution.get("project_id") != PROJECT
            or execution.get("workspace_id") != WORKSPACE
            or not str(execution.get("session_id", "")).startswith("telco-")
        ):
            raise AccessDenied("Execution belongs to another scope")
        return execution

    def present(self, token: str, execution_id: str) -> dict[str, Any]:
        execution = self.execution(token, execution_id)
        status = execution.get("status")
        try:
            locale = execution_locale(execution.get("message"))
        except ValueError:
            raise EngineUnavailable("Invalid execution presentation context") from None
        public: dict[str, Any] = {"execution_id": execution_id, "status": status, "locale": locale}
        if status == "suspended":
            interrupts = execution.get("suspend_context", {}).get("interrupts", [])
            if len(interrupts) != 1:
                raise JourneyConflict("Unexpected review frontier")
            review = interrupts[0].get("value", {})
            action = review.get("action", {})
            arguments = action.get("arguments", {})
            generation = execution.get("suspend_generation")
            if (
                review.get("contract") != "openai-engine-review-v2"
                or review.get("requesting_user_id") != execution["user_id"]
                or review.get("allowed_decisions") != ["approve", "reject"]
                or action.get("tool_name") != "telco_simulate_plan_change"
                or action.get("tool_call_id") != "journey-plan-change"
                or set(arguments) != {"plan_id", "monthly_minor", "proposal_id"}
                or arguments["plan_id"] not in ("fiber-500", "fiber-1000")
                or type(arguments["monthly_minor"]) is not int
                or not 0 <= arguments["monthly_minor"] <= 999999
                or not isinstance(arguments["proposal_id"], str)
                or len(arguments["proposal_id"]) != 64
                or type(generation) is not int
                or generation < 1
            ):
                raise JourneyConflict("Unexpected review contract")
            projection = {
                "execution_id": execution_id,
                "requester": execution["user_id"],
                "generation": generation,
                "review": review,
            }
            digest = hashlib.sha256(
                json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            public.update(action=arguments, action_digest=digest, generation=generation)
        elif status == "completed":
            raw = execution.get("result")
            if isinstance(raw, dict) and set(raw) == {"response"}:
                raw = raw["response"]
            result = json.loads(raw) if isinstance(raw, str) else raw
            if (
                not isinstance(result, dict)
                or result.get("contract") != "telecom-journey-v1"
                or not isinstance(result.get("text"), str)
                or len(result["text"]) > 8000
                or result.get("status")
                not in ("completed", "rejected", "expired", "needs_information")
                or not isinstance(result.get("specialists"), list)
                or any(
                    name not in ("financial", "technical", "sales")
                    for name in result["specialists"]
                )
            ):
                raise EngineUnavailable("The deployed agent does not match the journey contract")
            try:
                result_locale = validated_locale(result.get("locale", "en-US"))
            except ValueError:
                raise EngineUnavailable("Invalid result locale") from None
            if result_locale != locale:
                raise EngineUnavailable("Execution/result locale mismatch")
            public.update(
                text=result["text"], specialists=result["specialists"], outcome=result["status"]
            )
        elif status in ("error", "cancelled"):
            public["text"] = {
                "en-US": "The execution did not complete. No successful result is claimed.",
                "pt-BR": ("A execução não foi concluída. "
                          "Nenhum resultado bem-sucedido é confirmado."),
                "es-ES": "La ejecución no se completó. No se confirma ningún resultado exitoso.",
            }[locale]
        elif status not in ("pending", "running", "resuming"):
            raise EngineUnavailable("Unexpected execution state")
        return public

    def send(self, token: str, conversation: UUID, message: str,
             locale: Locale | None = None) -> dict[str, Any]:
        actor = self.identity.principal(token)
        session = session_id(actor.user_id, conversation)
        selected = validated_locale(locale) if locale is not None else self.turn_locale(token)
        wire = Turn(locale=selected, message=message).wire() if self.localized_turns else message
        result = self.engine.invoke(actor.user_id, session, wire)
        execution_id = str(UUID(result["execution_id"]))
        execution = self.execution(token, execution_id)
        if execution["session_id"] != session:
            raise JourneyConflict("Invocation session mismatch")
        if self.localized_turns and execution.get("message") != wire:
            raise JourneyConflict("Invocation message mismatch")
        return self.present(token, execution_id)

    def latest(self, token: str, conversation: UUID) -> dict[str, Any]:
        user = self.identity.principal(token).user_id
        session = session_id(user, conversation)
        execution_id = self.engine.latest(session)
        if execution_id is None:
            return {"status": "empty"}
        if self.execution(token, execution_id)["session_id"] != session:
            raise JourneyConflict("Latest execution session mismatch")
        return self.present(token, execution_id)

    def decide(self, token: str, execution_id: str, digest: str, decision: str) -> dict[str, Any]:
        if decision not in ("approve", "reject"):
            raise ValueError("Invalid decision")
        pending = self.present(token, execution_id)
        if pending["status"] != "suspended" or pending.get("action_digest") != digest:
            raise JourneyConflict("Review changed; reload the exact pending action")
        # Reauthenticate just before the native atomic generation-checked resume.
        self.execution(token, execution_id)
        self.engine.resume(execution_id, pending["generation"], decision)
        return self.present(token, execution_id)
