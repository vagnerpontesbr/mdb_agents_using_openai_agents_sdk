"""Native publication sequencing with the pinned AER parser; Engine transport is doubled."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_engine_sdk.models import AgentInput, RequestContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.workflow import attempt_context_scope
from agent_engine_runner_shared.server.aer import AERServer

from openai_engine_adapter.adapter import UnsupportedContract
from openai_engine_adapter.knowledge_review import KnowledgeExecution, PublicationRequest, PREFIX
from openai_engine_adapter.review import ReviewDecision


class KnowledgeReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ctx = RequestContext(user_id='owner', execution_id='exec', session_id='session', workspace_id='ws')
        self.attempt = AttemptContext(workflow_identity=WorkflowIdentity(
            tenant_scope=TenantScope(org_id='org', project_id='project', workspace_id='ws'),
            execution_id='exec', session_id='session'), attempt_id='attempt', fencing_token=1)
        self.request = PublicationRequest(job_id='a'*64, metadata={'checksum': 'b'*64})
        self.tools = MagicMock()
        self.tools.execute_tool.return_value = json.dumps(
            {'request_digest': self.request.digest(), 'requester': 'owner'})
        self.agent = KnowledgeExecution(SimpleNamespace(), lambda *args: SimpleNamespace(tools=self.tools))
        self.deadline = SimpleNamespace(expired=lambda: False, expires_at=2000000000.0)
        self.settle = AsyncMock()
        for item in (
            patch('openai_engine_adapter.knowledge_review.get_current_oe_url', return_value='https://oe.invalid'),
            patch('openai_engine_adapter.knowledge_review.WorkflowClient'),
            patch('openai_engine_adapter.knowledge_review.record_deadline', return_value=self.deadline),
            patch('openai_engine_adapter.knowledge_review.settle_execution', self.settle),
        ):
            item.start()
            self.addCleanup(item.stop)

    async def invoke(self):
        with attempt_context_scope(self.attempt):
            return await AERServer._execute_via_agent_stream(SimpleNamespace(), self.agent,
                self.ctx, AgentInput(payload={'message': PREFIX + self.request.model_dump_json()}),
                'https://oe.invalid', 'exec')

    async def test_native_approval_precedes_exact_receipt(self):
        with patch('openai_engine_adapter.knowledge_review.request_review',
                   return_value=ReviewDecision(decision='approve')) as review:
            result = json.loads((await self.invoke()).content)
        self.assertEqual(review.call_args.kwargs['action'].arguments, self.request.model_dump())
        self.assertEqual(result['request_digest'], self.request.digest())
        self.assertEqual(result['status'], 'approved')
        self.tools.execute_tool.assert_called_once()
        self.settle.assert_awaited_once()

    async def test_rejected_or_expired_review_cannot_issue_receipt(self):
        for decision, expired, status in [('reject', False, 'rejected'), ('approve', True, 'expired')]:
            self.deadline.expired = lambda: expired
            with patch('openai_engine_adapter.knowledge_review.request_review',
                       return_value=ReviewDecision(decision=decision)):
                result = json.loads((await self.invoke()).content)
            self.assertEqual(result['status'], status)
        self.tools.execute_tool.assert_not_called()

    async def test_unknown_review_outcome_never_completes(self):
        with patch('openai_engine_adapter.knowledge_review.request_review', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                await self.invoke()
        self.tools.execute_tool.assert_not_called()
        self.settle.assert_not_awaited()

    async def test_other_requester_receipt_is_rejected(self):
        self.tools.execute_tool.return_value = {'request_digest': self.request.digest(), 'requester': 'other'}
        with patch('openai_engine_adapter.knowledge_review.request_review',
                   return_value=ReviewDecision(decision='approve')):
            with self.assertRaises(UnsupportedContract):
                await self.invoke()
        self.settle.assert_not_awaited()
