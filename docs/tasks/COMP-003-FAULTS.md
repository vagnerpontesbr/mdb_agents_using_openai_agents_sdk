# COMP-003-FAULTS: Local cancellation boundaries

- Status: Done for the bounded local cancellation contract; hosted outage coverage remains separate
- Parent: [COMP-003](COMP-003-HOSTED.md)
- Relevant decisions: [ADR-0017](../adr/0017-two-cluster-memory-boundary.md), [ADR-0018](../adr/0018-engine-feature-precedence.md)

## Scope and acceptance

Exercise cancellation while each synchronous Engine boundary is already running: historical-memory read, model invocation and remote read-tool execution. Require cancellation to propagate, no terminal result event, no later-stage dispatch and no adapter retry. Reusing the same execution result must fail without dispatching again. This tests the existing adapter without changing platform policy or adding a cancellation owner.

## Evidence

On 2026-10-29, all three [cancellation tests](../../tests/hosted_contract/test_cancellation_faults.py) passed using the real OpenAI Runner and signature-checked Engine doubles in the frozen hosted-runtime environment. Thread/event barriers ensure cancellation occurs during the synchronous operation rather than before dispatch. The tests explicitly release the blocked operation afterward and verify its late completion cannot publish a result or start the next stage. No credentials, provider calls or deployment are involved.

Run from the repository root:

```sh
uv run --project compatibility/hosted-runtime --frozen python -m unittest discover -s tests/hosted_contract -p test_cancellation_faults.py -v
```

The separate adapter project initially failed interpreter discovery; the existing hosted-runtime environment was used without changing Python targets or dependencies. It pins OpenAI Agents SDK 0.24.0 and Engine SDK/runner 0.11.11 on Python 3.15.2.

## Limits and next acceptance

Cancellation of the async caller does not stop an already-running synchronous thread or remote Engine operation. The tests deliberately prove that limitation as well as suppression of its late output. They do not establish cancellation of provider billing, remote side effects, transport deadlines, interruption of a permanently blocked thread, hosted sandbox cleanup or recovery under a backing-service outage. Engine remains the platform budget/cancellation authority; a future write tool still requires domain idempotency for uncertain outcomes.

Existing model-timeout, memory-failure and Engine-denial tests cover local fail-closed behavior. A bounded hosted test of a backing-service failure and independent allowed/denied service-credential operations remains distinct from this cancellation proof. Do not infer least privilege from synthetic tenant filters or from a working administrative MCP connection. Preserve the two-cluster boundary and avoid disrupting shared Engine memory to inject failures.

The [official OpenAI example](https://developers.openai.com/cookbook/examples/partners/aws/chatgpt_agents_sdk_aws_agentcore_cookbook/notebooks/chatgpt_agents_sdk_aws_agentcore_cookbook#2-follow-a-request-through-the-agent) confirms the `stop_on_first_tool` orchestration pattern, but does not establish Engine cancellation semantics. Those claims above are limited to the pinned local tests.
