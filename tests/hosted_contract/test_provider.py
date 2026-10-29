"""Real OpenAI HTTP serialization with an in-memory HTTP transport."""

import json
import os
import unittest
from unittest.mock import patch

import httpx
from openai import AsyncOpenAI, RateLimitError
from agent_engine_sdk.models import Message
from agent_engine_runner_shared.secure_llm_proxy import SecureLLMProxy

from openai_engine_adapter.adapter import UnsupportedContract
from openai_engine_adapter.invoice import app, lookup_invoice
from openai_engine_adapter.openai_provider import OpenAIModelConfig, OpenAIProvider


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.body = {
            "id": "resp-synthetic", "object": "response", "created_at": 0,
            "status": "completed", "model": "gpt-5.6-luna",
            "output": [{"type": "function_call", "id": "fc-1", "call_id": "call-1",
                        "name": "lookup_invoice", "arguments": '{"invoice_id":"demo-1"}'}],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }
        def respond(request):
            self.requests.append(request)
            return httpx.Response(self.status, json=self.body)

        def client(**kwargs):
            self.assertEqual(kwargs["max_retries"], 0)
            return AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))

        self.env = patch.dict(os.environ, {"RUNNER_MODE": "tool", "OPENAI_API_KEY": "synthetic-key"})
        self.env.start()
        self.client = patch("openai_engine_adapter.openai_provider.AsyncOpenAI", side_effect=client)
        self.client.start()
        self.provider = OpenAIProvider(OpenAIModelConfig(), tools=[app.tools()[0].schema()])
        self.messages = [Message(role="user", content="Read demo-1")]

    def tearDown(self):
        self.client.stop()
        self.env.stop()

    async def test_responses_http_and_engine_chunk_roundtrip(self):
        chunks = [chunk async for chunk in self.provider.astream(self.messages, parallel_tool_calls=False)]
        result = SecureLLMProxy.response_from_stream_chunks(chunks)
        self.assertEqual(result.tool_calls[0].id, "call-1")
        self.assertEqual(result.tool_calls[0].args, {"invoice_id": "demo-1"})
        self.assertEqual(result.usage.total_tokens, 15)
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.openai.com/v1/responses")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "gpt-5.6-luna")
        self.assertFalse(body["store"])
        self.assertFalse(body["parallel_tool_calls"])
        self.assertEqual(body["tools"][0]["name"], "lookup_invoice")

    async def test_provider_not_callable_from_agent_sandbox(self):
        with patch.dict(os.environ, {"RUNNER_MODE": "aer"}), self.assertRaises(UnsupportedContract):
            await self.provider.ainvoke(self.messages)
        self.assertEqual(self.requests, [])

    async def test_rate_limit_not_retried_by_provider(self):
        self.status = 429
        self.body = {"error": {"message": "Synthetic rate limit", "type": "rate_limit_error"}}
        with self.assertRaises(RateLimitError):
            await self.provider.ainvoke(self.messages)
        self.assertEqual(len(self.requests), 1)

    async def test_incomplete_response_not_released(self):
        self.body["status"] = "incomplete"
        with self.assertRaises(UnsupportedContract):
            await self.provider.ainvoke(self.messages)

    async def test_unknown_options_fail_before_http(self):
        with self.assertRaises(UnsupportedContract):
            await self.provider.ainvoke(self.messages, response_format={"type": "json_object"})
        self.assertEqual(self.requests, [])

    async def test_synthetic_invoice_scope(self):
        self.assertEqual(lookup_invoice("demo-1")["amount_minor"], 7990)
        with self.assertRaises(PermissionError):
            lookup_invoice("other")


if __name__ == "__main__":
    unittest.main()
