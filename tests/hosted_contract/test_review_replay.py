"""Real Runner/proxies/AER replay with a serialized, explicitly fake OE ledger."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_engine_sdk.models import AgentInput, RequestContext, LLMStreamChunk, ToolCallChunk
from agent_engine_runner_shared import hooks
from agent_engine_runner_shared.context import set_execution_context, clear_execution_context
from agent_engine_runner_shared.models import InterruptResult
from agent_engine_runner_shared.server.aer import AERServer
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ActivityContext, ActivityOutcome
from agent_engine_runner_shared.workflow import attempt_context_scope
from agent_engine_runner_shared.workflow.activity import completed_outcome, suspended_outcome
from agent_engine_runner_shared.workflow.client import ActivityDispatch, ActivityReplay

from openai_engine_adapter.review_invoice import app
from openai_engine_adapter.memory_invoice import app as memory_app
from agent_engine_runner_shared.workflow.memory import DurableMemoryState


class ReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_runner_and_proxies_replay_without_provider_or_tool_redispatch(self):
        await self.exercise_replay(managed=False)

    async def test_engine_memory_projection_replays_stable_writes_and_empty_review_ack(self):
        await self.exercise_replay(managed=True)

    async def exercise_replay(self, *, managed):
        hooks.reset_hooks()
        self.addCleanup(hooks.reset_hooks)
        identity = WorkflowIdentity(tenant_scope=TenantScope(org_id="org", project_id="project", workspace_id="workspace"),
                                    session_id="session", execution_id="exec")
        ctx = RequestContext(execution_id="exec", user_id="user", session_id="session", workspace_id="workspace")
        commands, outcomes = {}, {}
        client = MagicMock()
        client.__enter__.return_value = client

        def start(command):
            ordinal = command.position.activity_ordinal
            # This fixture is not evidence of server-side hash/fence validation.
            if ordinal in commands:
                old = commands[ordinal]
                self.assertEqual(old.semantic_input, command.semantic_input)
                self.assertEqual(old.activity_name, command.activity_name)
                return ActivityReplay(ActivityOutcome.FromString(outcomes[ordinal]))
            commands[ordinal] = type(command).FromString(command.SerializeToString())
            return ActivityDispatch(ActivityContext(workflow_identity=identity, attempt_id=command.attempt_id,
                                    fencing_token=command.fencing_token, activity_id=str(ordinal)))

        client.start_activity.side_effect = start
        client.report_outcome.side_effect = lambda outcome: outcomes.__setitem__(int(outcome.activity_id), outcome.SerializeToString())
        settlement = MagicMock()
        settlement.__aenter__ = AsyncMock(return_value=settlement)
        settlement.__aexit__ = AsyncMock(return_value=False)
        async def finalize(command):
            if not command.suspensions:
                return []
            pause, = command.suspensions
            self.assertEqual(pause.suspension.reason, "agent_interrupt")
            outcome = suspended_outcome(ActivityContext(workflow_identity=identity,
                attempt_id=command.attempt_id, fencing_token=command.fencing_token,
                activity_id="3"), reason="agent_interrupt", context={})
            outcomes[3] = outcome.SerializeToString()
            return [SimpleNamespace(position=pause.position, outcome=outcome)]
        settlement.finalize_step = AsyncMock(side_effect=finalize)
        settlement.complete_execution = AsyncMock()
        invoice = {"invoice_id": "demo-1", "amount_minor": 7990, "currency": "USD", "synthetic": True}

        async def leg(number):
            wrapper = SecureToolWrapper("https://oe.invalid", "exec",
                durable_memory=DurableMemoryState("Read demo-1") if managed else None)
            wrapper._workflow = client
            tokens = set_execution_context(execution_id="exec", wrapper=wrapper, oe_url="https://oe.invalid",
                                           user_id="user", session_id="session", workspace_id="workspace")
            attempt = AttemptContext(workflow_identity=identity, attempt_id=f"attempt-{number}", fencing_token=number,
                                     replay_mode=number > 1)
            request = ctx if number == 1 else ctx.model_copy(update={"resume": True, "resume_data": {"3": {"decision": "approve"}}})
            try:
                with attempt_context_scope(attempt):
                    return await AERServer._execute_via_agent_stream(
                        SimpleNamespace(), (memory_app if managed else app).get_agent(), request, AgentInput(payload={"message": "Read demo-1"}),
                        "https://oe.invalid", "exec",
                    )
            finally:
                clear_execution_context(tokens)

        def provider(*args, **kwargs):
            yield LLMStreamChunk(id="response-1", content="", tool_calls=[ToolCallChunk(
                id="call-1", name="lookup_invoice", args='{"invoice_id":"demo-1"}', index=0,
            )])

        with patch("agent_engine_runner_shared.workflow.activity.WorkflowClient", return_value=client), \
             patch("openai_engine_adapter.review_execution.WorkflowClient", return_value=client), \
             patch("openai_engine_adapter.review_execution.AsyncWorkflowClient", return_value=settlement), \
             patch("agent_engine_runner_shared.workflow.settlement.AsyncWorkflowClient", return_value=settlement), \
             patch.object(SecureLLMProxy, "_stream_llm", side_effect=provider) as model_dispatch, \
             patch.object(SecureToolWrapper, "_execute_tool_native", return_value=(memory_app.get_tool_definitions()[0].callable(invoice_id="demo-1") if managed else invoice)) as tool_dispatch:
            suspended = await leg(1)
            self.assertIsInstance(suspended, InterruptResult)
            self.assertEqual(sorted(commands), [1, 2, 3])
            review = ActivityContext(workflow_identity=identity, attempt_id="attempt-1", fencing_token=1, activity_id="3")
            outcomes[3] = completed_outcome(review, {"decision": "approve"}).SerializeToString()
            resumed = await leg(2)
        self.assertEqual(json.loads(resumed.content), invoice)
        model_dispatch.assert_called_once()
        tool_dispatch.assert_called_once()
        self.assertEqual(client.start_activity.call_count, 6)
        self.assertEqual(client.report_outcome.call_count, 2)
        settlement.complete_execution.assert_called_once()
        self.assertEqual(hooks.get_workflow_adapter(), ("openai-engine-review", "3" if managed else "1"))
        if managed:
            batches = [call.args[0].memory_writes for call in client.ensure_memory_written.call_args_list]
            self.assertEqual([len(batch) for batch in batches], [2, 1, 2, 1, 0])
            self.assertEqual(batches[0], batches[2])
            self.assertEqual(batches[1], batches[3])
            self.assertEqual(len({write.id for batch in batches for write in batch}), 3)
        else:
            client.ensure_memory_written.assert_not_called()
