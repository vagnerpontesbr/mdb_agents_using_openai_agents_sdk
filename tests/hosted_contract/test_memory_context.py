"""Real Engine memory-read activity replay; transport and retrieval are doubled."""
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import MagicMock, patch
from agent_engine_sdk.models import RequestContext
from agent_engine_sdk_memory.models import ContextResponse, ContextMetadata
from agent_engine_runner_shared.runtime import TenantRuntime
from agent_engine_runner_shared.context import set_execution_context, clear_execution_context
from agent_engine_runner_shared.generated.workflow.v1.activity_pb2 import ActivityContext
from agent_engine_runner_shared.generated.workflow.v1.runtime_pb2 import AttemptContext
from agent_engine_runner_shared.generated.workflow.v1.common_pb2 import WorkflowIdentity, TenantScope
from agent_engine_runner_shared.workflow import attempt_context_scope
from agent_engine_runner_shared.workflow.client import ActivityDispatch, ActivityReplay
from openai_engine_adapter.memory_context import retrieve_context
from openai_engine_adapter.adapter import UnsupportedContract


class MemoryContextTests(unittest.TestCase):
    def setUp(self):
        self.identity = WorkflowIdentity(tenant_scope=TenantScope(org_id='org', project_id='project', workspace_id='workspace'),
                                        execution_id='exec', session_id='session')
        self.ctx = RequestContext(execution_id='exec', session_id='session', workspace_id='workspace', user_id='user')
        self.runtime = SimpleNamespace(memory_enabled=True, org_id='org', project_id='project', _memory_engine=object())
        self.runtime.build_context_from_sources = MethodType(TenantRuntime.build_context_from_sources, self.runtime)
        self.client = MagicMock()
        self.tokens = set_execution_context(execution_id='exec', oe_url='https://oe.invalid', wrapper=SimpleNamespace(workflow=self.client),
                                           user_id='user', session_id='session', workspace_id='workspace')
        self.addCleanup(clear_execution_context, self.tokens)
        self.response = ContextResponse(formatted_context='SYNTHETIC memory', metadata=ContextMetadata(
            source_outcomes=[{'source':s, 'effective_mode':'hybrid', 'requested_mode':'hybrid', 'count':1, 'error':None, 'retryable':False} for s in ('semantic','episodic')]))

    def attempt(self, number=1):
        return AttemptContext(workflow_identity=self.identity, attempt_id=str(number), fencing_token=number, replay_mode=number>1)

    def test_real_runtime_reads_once_and_replays_same_context(self):
        activity = ActivityContext(workflow_identity=self.identity, attempt_id='1', fencing_token=1, activity_id='read')
        self.client.start_activity.return_value = ActivityDispatch(activity)
        with patch('agent_engine_runner_shared.memory.build_context_from_sources', return_value=self.response) as read:
            with attempt_context_scope(self.attempt()):
                first = retrieve_context(self.runtime, self.ctx, 'marker?')
            outcome = self.client.report_outcome.call_args.args[0]
            self.client.start_activity.return_value = ActivityReplay(outcome)
            with attempt_context_scope(self.attempt(2)):
                second = retrieve_context(self.runtime, self.ctx, 'marker?')
        self.assertEqual(first, second)
        read.assert_called_once()
        self.assertEqual(read.call_args.kwargs['user_id'], 'user')
        self.assertEqual(read.call_args.kwargs['session_id'], 'session')
        self.assertEqual(read.call_args.kwargs['max_tokens'], 2048)
        self.assertEqual([s.source for s in read.call_args.kwargs['sources']], ['semantic', 'episodic'])
        self.assertEqual(self.client.report_outcome.call_count, 1)

    def test_degraded_or_missing_metadata_is_not_an_empty_success(self):
        self.runtime.build_context_from_sources = MagicMock(return_value=ContextResponse(formatted_context='', metadata=ContextMetadata()))
        with attempt_context_scope(self.attempt()), self.assertRaises(UnsupportedContract):
            retrieve_context(self.runtime, self.ctx, 'marker?')

    def test_wrong_identity_rejected_before_retrieval(self):
        self.runtime.build_context_from_sources = MagicMock()
        for user in (None, 'another-user'):
            self.ctx.user_id = user
            with attempt_context_scope(self.attempt()), self.assertRaises(UnsupportedContract):
                retrieve_context(self.runtime, self.ctx, 'marker?')
        self.runtime.build_context_from_sources.assert_not_called()
