"""Native Engine publication review; MongoDB activation remains a backend domain operation."""

import asyncio
import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from agent_engine_sdk.models import StreamEvent
from agent_engine_runner_shared import hooks
from agent_engine_runner_shared.context import get_current_oe_url, get_current_user_id
from agent_engine_runner_shared.generated.workflow.v1.state_pb2 import StateSnapshot
from agent_engine_runner_shared.workflow import (
    WorkflowClient, allocate_activity_ordinal, current_attempt_context, settle_execution,
)
from agent_engine_runner_shared.workflow.protojson import json_to_proto_struct

from .adapter import EngineBindings, RemoteReadTool, UnsupportedContract
from .app import OpenAIEngineApp
from .journey import JourneyExecution
from .journey_domain import BusinessResult, ChangeQuery, EmptyQuery, InvoiceQuery, PlanQuery
from .journey import telco_read_invoice, telco_check_connection, telco_offer_plan, telco_simulate_plan_change
from .openai_provider import OpenAIModelConfig, provider_factory
from .review import ReviewAction, ReviewInterrupt, request_review
from .review_deadline import record_deadline
from .review_execution import finalize_review_interrupt

PREFIX = "__telecom_document_review__:"


class PublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    job_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata: dict[str, JsonValue]

    def digest(self):
        return hashlib.sha256(json.dumps(self.model_dump(mode="json"),
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PublicationToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class PublicationToolReceipt(PublicationToolInput):
    requester: str = Field(min_length=1, max_length=128)


class KnowledgeExecution(JourneyExecution):
    async def stream(self, ctx, input):
        message = input.payload.get("message")
        if not isinstance(message, str) or not message.startswith(PREFIX):
            async for event in super().stream(ctx, input):
                yield event
            return
        if len(message) > 4000:
            raise UnsupportedContract("Publication request exceeds its bound")
        request = PublicationRequest.model_validate_json(message[len(PREFIX):], strict=True)
        attempt = current_attempt_context()
        if attempt is None or not get_current_oe_url():
            raise UnsupportedContract("Publication requires a durable Engine attempt")
        identity = attempt.workflow_identity
        if ((ctx.execution_id, ctx.session_id, ctx.workspace_id) !=
                (identity.execution_id, identity.session_id, identity.tenant_scope.workspace_id)
                or not ctx.user_id or not attempt.attempt_id or not attempt.fencing_token
                or ctx.metadata or ctx.previous_execution_cancelled
                or ctx.resume and (not attempt.replay_mode or not isinstance(ctx.resume_data, dict))
                or not ctx.resume and ctx.resume_data is not None):
            raise UnsupportedContract("Publication execution scope mismatch")
        action = ReviewAction(tool_name="telco_publish_knowledge",
            tool_call_id="document-publication", arguments=request.model_dump(mode="json"))
        ordinal = allocate_activity_ordinal("publication-deadline")
        def deadline_call():
            with WorkflowClient(get_current_oe_url()) as client:
                return record_deadline(client=client, context=ctx, action=action,
                                       ttl_seconds=300, ordinal=ordinal)
        deadline = await asyncio.to_thread(deadline_call)
        ordinal = allocate_activity_ordinal("publication-review")
        def review_call():
            with WorkflowClient(get_current_oe_url()) as client:
                return request_review(client=client, context=ctx, action=action,
                                      activity_ordinal=ordinal, deadline=deadline)
        try:
            decision = await asyncio.to_thread(review_call)
        except ReviewInterrupt as interrupt:
            decision = await finalize_review_interrupt(attempt, interrupt)
            if isinstance(decision, StreamEvent):
                yield decision
                return
        status = "rejected" if decision.decision == "reject" else (
            "expired" if deadline.expired() else "approved")
        if status == "approved":
            raw = await asyncio.to_thread(self.bindings(ctx, []).tools.execute_tool,
                "telco_publish_knowledge", {"request_digest": request.digest()},
                tool_call_id="document-publication", is_local=False, on_unknown_outcome="fail")
            receipt = (PublicationToolReceipt.model_validate_json(raw, strict=True)
                       if isinstance(raw, str) else PublicationToolReceipt.model_validate(raw, strict=True))
            if receipt.requester != ctx.user_id or receipt.request_digest != request.digest():
                raise UnsupportedContract("Publication receipt scope mismatch")
        result = {"contract": "telecom-document-review-v1", "status": status,
                  "request": request.model_dump(mode="json"), "request_digest": request.digest(),
                  "requester": ctx.user_id, "expires_at": deadline.expires_at}
        encoded = json.dumps(result, sort_keys=True, separators=(",", ":"))
        await settle_execution(attempt, StateSnapshot(properties=json_to_proto_struct({
            "adapter_contract": "telecom-document-review-v1", "response": encoded})))
        yield StreamEvent(event="result", data={"response": encoded})


class KnowledgeApp(OpenAIEngineApp):
    knowledge_enabled = True
    def get_agent(self, callbacks=None, *, graph=None):
        super().get_agent(callbacks, graph=graph)
        hooks.register_workflow_adapter("telecom-journey", "8")
        def bindings(context, schemas):
            return EngineBindings.from_runtime(context=context, schemas=schemas,
                llm_id=self.llm_id, model_name=self.model_name, managed_memory=True)
        return KnowledgeExecution(self, bindings)


app = KnowledgeApp(name="agentsdk", instructions="Telecom journey and document review",
    llm_id="invoice-model", model_name="gpt-5.6-luna", provider_builder=OpenAIModelConfig,
    provider_adapter_factory=provider_factory, managed_memory=True, retrieve_memory=True)

for name, function, arguments in (
    ("telco_read_invoice", telco_read_invoice, InvoiceQuery),
    ("telco_check_connection", telco_check_connection, EmptyQuery),
    ("telco_offer_plan", telco_offer_plan, PlanQuery),
    ("telco_simulate_plan_change", telco_simulate_plan_change, ChangeQuery),
):
    app.tool(contract=RemoteReadTool(name, name, arguments, BusinessResult))(function)


@app.tool(contract=RemoteReadTool("telco_publish_knowledge", "Confirm exact publication request",
                                PublicationToolInput, PublicationToolReceipt))
def telco_publish_knowledge(request_digest):
    # This receipt alone is NOT approval. The backend must read the completed
    # Engine execution above, whose result is settled only after native review.
    return {"request_digest": request_digest, "requester": get_current_user_id()}


from .knowledge_tools import KnowledgeQuery, IngestionQuery, search_knowledge, request_ingestion

app.tool(contract=RemoteReadTool('telco_search_knowledge', 'Find approved technical procedures',
                                KnowledgeQuery, BusinessResult))(search_knowledge)
app.tool(contract=RemoteReadTool('telco_request_ingestion', 'Register an uploaded PDF for processing',
                                IngestionQuery, BusinessResult))(request_ingestion)
