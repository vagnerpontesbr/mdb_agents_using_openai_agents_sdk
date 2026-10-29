# COMP-003-FAULTS: Local cancellation boundaries

- Status: Bounded local and injected hosted dependency-failure controls passed; restored recall positive control passed. Broader production resilience remains separate.
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


## HTTP delivery and voice dependency faults: bounded follow-up

Four new [loopback HTTP tests](../../tests/compatibility/test_voice_http_faults.py)
passed in the frozen Python 3.15.2 environment, using the real HTTP handler and
sockets with doubled speech/Engine boundaries. They verify silent/malformed PCM
rejection before provider dispatch, at most three transcription attempts, a
provider timeout with no follow-up chat/retry, and concurrent duplicate denial.
A real TCP reset during a blocked doubled operation verifies exactly one dispatch,
preservation of the completed outcome, and refusal to dispatch that request again.

The TCP-reset test exposed an error-reporting defect: failed delivery could mark
completed work as a provider failure and try a second response. The handler now
records `client_delivery_lost` separately and preserves the execution outcome.
This does not cancel the remote operation, restore lost audio, or prove any
hosted outage behavior. The local probe also resolves the actual bound port when
`--port 0` is used by tests. No shared Engine service or deployment was changed.

[Live voice fault evidence](../../compatibility/voice-noise-fault-evidence.json)
records one generated English fixture mixed with seeded white noise at 10 dB SNR.
The transcript missed required fixture words and was rejected before any Engine
call. A real OpenAI request using a synthetic invalid key returned 401 and also
stopped before Engine dispatch. `passed` in this report means these two bounded
fail-closed checks passed; noisy-speech recognition did not succeed. An earlier
[noise attempt](../../compatibility/voice-noise-first-attempt-evidence.json) stopped
at rejection before the provider-denial check; its failure evidence is preserved.

Reproduce the explicit live probe:

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/check_voice_noise_faults.py --allow-live --output compatibility/voice-noise-fault-evidence.json
```

All 74 compatibility tests passed after these changes. Database-role positive/
negative controls are now recorded in [COMP-005](COMP-005-DEMO-AUTH.md#restricted-application-identity-passes),
and the user accepted the Engine CLI credential exception. The remaining limits
are successful recognition under controlled noise and fault injection against a
hosted backing service; local doubles and provider authentication denial must not
be labeled a hosted service-outage proof.


## Isolated hosted dependency-failure probe passes

The opt-in `dependency_failure_invoice:app` fixture reserves a loopback socket
without listening and attempts one connection with a one-second timeout inside
the Tool Pod. Refusal or timeout becomes a typed dependency failure; the fixture
cannot return an invoice. This injects dependency unavailability without stopping
shared MongoDB/Engine services or changing credentials. Only the exact synthetic
invoice ID `demo-service-unavailable` is accepted.

The fixture passed 61 hosted-contract tests on macOS and Linux/amd64. Initial
macOS testing demonstrated timeout rather than immediate refusal; both OS failure
modes are now handled, with no retry. The staged manifest selects this fixture,
while the repository's default manifest is unchanged. Source hashes and the
prior recall build for restoration are recorded in
[hosted evidence](../../compatibility/hosted-dependency-failure-evidence.json).
Remote build `bld_01M64N7WA4D2R9FZDHDMECH6MV` completed its image publication.
Deployment `deploy-0feb3249` succeeded at 20:30:06.022Z after transient
certificate/OE readiness and rollout waits. A general `agentengine status` query
returned an older deployment reference; the exact deployment ID was checked
before invocation.

Session `phase0-dependency-failure-a1edc5321c1e`, execution
`1900b0a9-7693-4e15-9a62-bda4fc17ede8`, produced exactly four structured logs:
one LLM start/success at step 1 and one tool start/error at step 2. The execution
finished with `status=error`, empty result, and the expected synthetic dependency
failure in both execution state and logs. All user/project/workspace/session/
execution scopes matched; the response had no further log page. CLI exit 1 alone
was not used as proof. No invoice was released and no second tool/model step was
observed in this bounded execution.

This closes bounded hosted propagation of an injected dependency-unavailability
error. It does not prove recovery from every real Atlas/OpenAI outage or remote
cancellation; those broader resilience guarantees remain implementation/operations
work. The previous recall build was restored successfully by `deploy-9c637560` at
20:33:55.797Z with OE, memory, agent and tool available. Positive execution
`9841af21-2393-492a-a22c-7895c069d7dc` in session
`phase0-restored-recall-bc0986191331` then completed native review and returned the
expected recalled marker and synthetic invoice. The normal demo build is active;
the failure fixture remains opt-in. The bounded Phase 0 fault gate is closed.


To reproduce only in the dedicated demo workspace, stage the opt-in fixture with
`scripts/prepare_hosted_invoice.py`, select
`openai_engine_adapter.dependency_failure_invoice:app` in the staged `agent.yaml`,
build/deploy it, then invoke `Read invoice demo-service-unavailable.` in a fresh
synthetic session. Require both the execution's terminal error/empty result and
its correlated model/tool logs; CLI failure alone is insufficient. Always restore
the recorded recall build and verify a normal native-review/memory-recall run.
This is a controlled synthetic diagnostic, not an instruction to stop a shared
backing service. The normal repository manifest does not select the failure app.
