"""Telecom journey deployment entrypoint; Engine owns durable work and review."""

import asyncio
import json

from agent_engine_runner_shared import hooks
from agent_engine_runner_shared.context import get_current_oe_url, get_current_user_id
from agent_engine_runner_shared.generated.workflow.v1.state_pb2 import StateSnapshot
from agent_engine_runner_shared.workflow import (
    WorkflowClient, allocate_activity_ordinal, current_attempt_context, settle_execution,
)
from agent_engine_runner_shared.workflow.protojson import json_to_proto_struct
from agent_engine_sdk.models import StreamEvent

from .adapter import EngineBindings, RemoteReadTool, UnsupportedContract
from .app import OpenAIEngineApp
from .journey_agent import JourneyAgent
from .journey_domain import (
    BusinessResult, ChangeQuery, EmptyQuery, InvoiceQuery, JourneyResult, PlanQuery,
    check_connection, offer_plan, read_invoice, simulate_change,
)
from .memory_context import retrieve_context
from .openai_provider import OpenAIModelConfig, provider_factory
from .review import ReviewAction, ReviewInterrupt, request_review
from .review_deadline import record_deadline
from .review_execution import finalize_review_interrupt


class JourneyExecution:
    def __init__(self, app, bindings):
        self.app, self.bindings = app, bindings

    def execute(self, ctx, input):
        return self.stream(ctx.model_copy(deep=True), input.model_copy(deep=True))

    async def stream(self, ctx, input):
        attempt = current_attempt_context()
        if attempt is None or not get_current_oe_url():
            raise UnsupportedContract("Journey requires a durable Engine attempt")
        identity = attempt.workflow_identity
        if ((ctx.execution_id, ctx.session_id, ctx.workspace_id) !=
                (identity.execution_id, identity.session_id, identity.tenant_scope.workspace_id)
                or not ctx.user_id or not attempt.attempt_id or not attempt.fencing_token
                or ctx.metadata or ctx.previous_execution_cancelled
                or ctx.resume and (not attempt.replay_mode or not isinstance(ctx.resume_data, dict))
                or not ctx.resume and ctx.resume_data is not None):
            raise UnsupportedContract("Journey execution identity/replay mismatch")
        fresh = ctx.model_copy(update={"resume": False, "resume_data": None})
        agent = JourneyAgent(self.bindings, lambda c, q: retrieve_context(self.app._runtime, c, q))
        result = JourneyResult.model_validate_json(
            (await agent.execute(fresh, input)).response["output"], strict=True)
        proposals = [r for r in result.results if r.kind == "proposal"]
        if len(proposals) > 1:
            raise UnsupportedContract("At most one proposal is allowed")
        if proposals:
            proposal = proposals[0]
            action = ReviewAction(tool_name="telco_simulate_plan_change",
                tool_call_id="journey-plan-change", arguments={
                    "plan_id": proposal.plan_id, "monthly_minor": proposal.monthly_minor,
                    "proposal_id": proposal.reference})
            ordinal = allocate_activity_ordinal("journey-review-deadline")
            def deadline_call():
                with WorkflowClient(get_current_oe_url()) as client:
                    return record_deadline(client=client, context=ctx, action=action,
                                           ttl_seconds=300, ordinal=ordinal)
            deadline = await asyncio.to_thread(deadline_call)
            review_ordinal = allocate_activity_ordinal("journey-review")
            def review_call():
                with WorkflowClient(get_current_oe_url()) as client:
                    return request_review(client=client, context=ctx, action=action,
                                          activity_ordinal=review_ordinal, deadline=deadline)
            try:
                decision = await asyncio.to_thread(review_call)
            except ReviewInterrupt as interrupt:
                decision = await finalize_review_interrupt(attempt, interrupt)
                if isinstance(decision, StreamEvent):
                    yield decision
                    return
            if decision.decision == "reject" or deadline.expired():
                status = "rejected" if decision.decision == "reject" else "expired"
                other_text = [r.text for r in result.results if r.kind != "proposal"]
                result = result.model_copy(update={"status": status,
                    "text": "\n\n".join([*other_text,
                        f"The plan-change simulation was {status}. No plan or charge changed."])})
            else:
                raw = await asyncio.to_thread(self.bindings(fresh, []).tools.execute_tool,
                    "telco_simulate_plan_change", action.arguments,
                    tool_call_id=action.tool_call_id, is_local=False, on_unknown_outcome="fail")
                receipt = (BusinessResult.model_validate_json(raw, strict=True) if isinstance(raw, str)
                           else BusinessResult.model_validate(raw, strict=True))
                if (receipt.account_ref != ctx.user_id or receipt.reference != proposal.reference
                        or receipt.kind != "simulation" or receipt.plan_id != proposal.plan_id
                        or receipt.monthly_minor != proposal.monthly_minor):
                    raise UnsupportedContract("Simulation receipt scope mismatch")
                result = result.model_copy(update={"text": "\n\n".join([
                    *[r.text for r in result.results if r.kind != "proposal"], receipt.text]),
                                                   "results": [*result.results, receipt]})
        encoded = result.model_dump_json()
        await settle_execution(attempt, StateSnapshot(properties=json_to_proto_struct({
            "adapter_contract": "telecom-journey-v1", "response": encoded})))
        yield StreamEvent(event="result", data={"response": encoded})


class JourneyApp(OpenAIEngineApp):
    def get_agent(self, callbacks=None, *, graph=None):
        # Reuse validated model discovery; its unused single-read agent is not executed.
        super().get_agent(callbacks, graph=graph)
        hooks.register_workflow_adapter("telecom-journey", "2")
        def bindings(context, schemas):
            return EngineBindings.from_runtime(context=context, schemas=schemas,
                llm_id=self.llm_id, model_name=self.model_name, managed_memory=True)
        return JourneyExecution(self, bindings)


app = JourneyApp(name="agentsdk", instructions="Telecom journey", llm_id="invoice-model",
    model_name="gpt-5.6-luna", provider_builder=OpenAIModelConfig,
    provider_adapter_factory=provider_factory, managed_memory=True, retrieve_memory=True)


@app.tool(contract=RemoteReadTool("telco_read_invoice", "Read own synthetic invoice",
                                InvoiceQuery, BusinessResult))
def telco_read_invoice(invoice_id):
    return read_invoice(get_current_user_id(), invoice_id).model_dump()


@app.tool(contract=RemoteReadTool("telco_check_connection", "Check synthetic connection",
                                EmptyQuery, BusinessResult))
def telco_check_connection():
    return check_connection(get_current_user_id()).model_dump()


@app.tool(contract=RemoteReadTool("telco_offer_plan", "Compare/propose eligible synthetic plan",
                                PlanQuery, BusinessResult))
def telco_offer_plan(plan_id, propose_change):
    return offer_plan(get_current_user_id(), plan_id, propose_change).model_dump()


@app.tool(contract=RemoteReadTool("telco_simulate_plan_change", "Produce approved simulation receipt",
                                ChangeQuery, BusinessResult))
def telco_simulate_plan_change(plan_id, monthly_minor, proposal_id):
    return simulate_change(get_current_user_id(), plan_id, monthly_minor, proposal_id).model_dump()
