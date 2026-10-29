"""Cancellation boundaries with the real Runner and blocked synchronous doubles."""

import asyncio
import threading
import unittest
from unittest.mock import create_autospec

from agent_engine_sdk.models import AgentInput, LLMResponse, LLMToolCall, RequestContext
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy
from agent_engine_runner_shared.secure_wrapper import SecureToolWrapper
from pydantic import BaseModel, ConfigDict

from openai_engine_adapter import EngineBindings, OpenAIEngineAgent, RemoteReadTool
from openai_engine_adapter.adapter import UnsupportedContract


class ReadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str


class ReadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_minor: int


class CancellationFaultTests(unittest.IsolatedAsyncioTestCase):
    async def check_cancelled_stage(self, stage):
        llm = create_autospec(SecureLLMProxy, instance=True)
        tools = create_autospec(SecureToolWrapper, instance=True)
        response = LLMResponse(content="", tool_calls=[
            LLMToolCall(id="synthetic-call", name="read_invoice", args={"invoice_id": "demo"}),
        ])
        llm.invoke.return_value = response
        tools.execute_tool.return_value = {"amount_minor": 7990}
        agent = OpenAIEngineAgent(
            instructions="Read synthetic invoices only.",
            tools=(RemoteReadTool("read_invoice", "Read invoice", ReadArgs, ReadResult),),
            bindings_factory=lambda ctx, schemas: EngineBindings(llm, tools),
        )
        loop = asyncio.get_running_loop()
        started, completed = asyncio.Event(), asyncio.Event()
        release = threading.Event()

        def blocked(*args, **kwargs):
            loop.call_soon_threadsafe(started.set)
            try:
                if not release.wait(timeout=5):
                    raise TimeoutError("Test failed to release synchronous double")
                return {"memory": "historical", "model": response,
                        "tool": {"amount_minor": 7990}}[stage]
            finally:
                loop.call_soon_threadsafe(completed.set)

        if stage == "memory":
            agent.memory_context_builder = blocked
        elif stage == "model":
            llm.invoke.side_effect = blocked
        else:
            tools.execute_tool.side_effect = blocked
        execution = agent.execute(
            RequestContext(execution_id="synthetic-exec", user_id="synthetic-user",
                           session_id="synthetic-session", workspace_id="synthetic-workspace"),
            AgentInput(payload={"text": "Read demo invoice"}),
        )
        events = []

        async def consume():
            async for event in execution:
                events.append(event)

        task = asyncio.create_task(consume())
        try:
            await asyncio.wait_for(started.wait(), timeout=3)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(events, [])
            # Async cancellation cannot stop an already-running sync Engine call.
            self.assertFalse(completed.is_set())
        finally:
            release.set()
            await asyncio.wait_for(completed.wait(), timeout=3)
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(task.cancelled())
        self.assertEqual(events, [])
        self.assertEqual(llm.invoke.call_count, 0 if stage == "memory" else 1)
        self.assertEqual(tools.execute_tool.call_count, 1 if stage == "tool" else 0)
        with self.assertRaises(UnsupportedContract):
            await execution
        self.assertEqual(llm.invoke.call_count, 0 if stage == "memory" else 1)
        self.assertEqual(tools.execute_tool.call_count, 1 if stage == "tool" else 0)

    async def test_cancel_during_memory_prevents_model_and_tool(self):
        await self.check_cancelled_stage("memory")

    async def test_cancel_during_model_prevents_late_tool_dispatch(self):
        await self.check_cancelled_stage("model")

    async def test_cancel_during_tool_suppresses_late_result_without_retry(self):
        await self.check_cancelled_stage("tool")
