**Latest local increment:** `expiry_memory_invoice:app` combines managed memory and a synthetic 60-second review deadline under workflow version 5. All 56 contract tests pass on macOS/Linux with remote transport doubled; sdist/wheel builds pass. The bounded combined hosted test now passes timely approval and expiry after sandbox release; the previous recall build was restored. Current status is authoritative in [COMP-003](../../docs/tasks/COMP-003-HOSTED.md); older deployment/status paragraphs below are historical checkpoints.

**Hosted proof:** The `gpt-5.6-luna` invoice flow now passes through Engine, including correlated model/tool traces and backend rejection of an out-of-fixture invoice. The authorized project policy additions have been applied. See [current evidence](../gpt56-luna-evidence.json) and [COMP-003](../../docs/tasks/COMP-003-HOSTED.md). Replay, approval/resume and hosted memory continuity remain unsupported by this bounded adapter. Earlier checkpoints below are historical.

**Current model update:** The user selected `gpt-5.6-luna`. A direct Responses API probe passed with the expected synthetic function call; see [provider evidence](../gpt56-luna-evidence.json). Local adapter defaults now select it. Deployment `deploy-fbbf9a94` now selects `gpt-5.6-luna`; the live Engine trace confirms that selection but blocks it under the project model allowlist. Shared project policy approval is required before a hosted positive control. Earlier model/build observations below are historical.

**Current build update:** The compact bundled Python 3.15.2 experiment now passes Linux tests and the remote VM build. See the [build runbook](../../docs/compatibility/PYTHON315_HOSTED.md) and [COMP-003](../../docs/tasks/COMP-003-HOSTED.md) for deployment status; earlier failed-build evidence below remains historical.

# Custom OpenAI Agents SDK / Engine adapter

Experimental local integration library implementing Engine `BaseAgent.execute` with the real OpenAI `Runner`. Authorized after the user-selected [Engine precedence decision](../../docs/adr/0018-engine-feature-precedence.md). This is not a vendor-supported adapter, a deployable application or a completed Phase 0 gate.

## Implemented contract

- One text request, one model call and at most one remote read tool. Tool output ends the run without another model synthesis step.
- Engine input/output types and a single-use awaitable/async-iterable result. Iteration emits one terminal `result` event; it is not token streaming.
- Engine `SecureLLMProxy.invoke` and `SecureToolWrapper.execute_tool`, preserving tool call IDs and arguments. `EngineBindings.for_request` constructs real proxies sharing one operational-step allocator per execution.
- Strict Pydantic argument/result validation; unknown tools, missing IDs, multiple calls and malformed responses fail. SDK tool errors surface as `UserError` with the original exception as cause. They are not converted into model answers or retried by the adapter.
- No direct model transport, local tool executor, SDK tracing export, memory writer, approval store or replay implementation.

## Trusted integration example

Run from the repository root with the frozen hosted-runtime environment. `oe_url`, `llm_id` and `model_name` below must come from trusted deployment configuration. The context must come from an authenticated, already-created Engine execution. This helper is not a public Engine client: inventing execution IDs or passing the API Gateway URL does not provision an execution.

```python
from pydantic import BaseModel, ConfigDict
from openai_engine_adapter import (
    EngineBindings, OpenAIEngineAgent, RemoteReadTool,
)

class InvoiceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str

class InvoiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str
    amount_minor: int
    currency: str

def create_agent(*, oe_url: str, llm_id: str, model_name: str):
    def bindings(context, schemas):
        return EngineBindings.for_request(
            oe_url=oe_url, context=context, schemas=schemas,
            llm_id=llm_id, model_name=model_name,
        )

    return OpenAIEngineAgent(
        instructions="Use the invoice tool to read the requested invoice.",
        tools=(RemoteReadTool(
            "lookup_invoice", "Read an authorized invoice",
            InvoiceArgs, InvoiceResult,
        ),),
        bindings_factory=bindings,
    )
```

The remote tool must already be registered in Engine and enforce customer/tenant permissions in its backend. `RemoteReadTool` is a trusted developer registration, not proof that an arbitrary remote tool has no side effects. No write or approval-dependent tools may be registered in this version. Do not forward caller-selected URLs, identities, credentials or tool registries into the factory.

Given that trusted runtime plumbing, invoke with `AgentInput(payload={"text": "Read invoice demo-1"})`. The response envelope is `{"output": ...}`: text for a model response, a JSON-encoded validated result for a tool response. Financial response rendering and factual correctness remain backend responsibilities.

## Validation

```bash
uv run --project compatibility/hosted-runtime --frozen \
  python -m unittest discover -s tests/hosted_contract -v
python3 -m unittest discover -s tests/compatibility -v
python3 scripts/check_repository.py
```

On 2026-10-28, 22 adapter/loader/provider tests passed on Python 3.15.2/macOS ARM64 with openai-agents 0.24.0 and Engine SDK/runner 0.11.11. Tests run the real Runner with signature-checked Engine transport doubles; the binding construction test uses actual proxy constructors without network. These establish local interface behavior only, not live policy, budget, guardrail, audit or replay enforcement.

## Explicit limitations and next acceptance gate

OpenAIEngineApp now implements the BaseApp loader and run entrypoint. The real TenantRuntime dispatch and AER terminal stream consumer pass local tests. The remote VM build was attempted and failed before installation because Python 3.15.2 was unavailable. Linux execution and live Engine execution remain unverified. The existing native-Agent rejection diagnostic remains valid. There are no registered workflow/suspend hooks and no deployment entrypoint that could misrepresent these gaps as support.

Resume/recovery requests, opaque state, history, handoffs, structured model outputs, custom SDK model settings, provider continuation IDs and token streaming are unsupported. Memory integration remains separate and no shared Anthropic model/key/gateway configuration was changed. Async cancellation stops awaiting a synchronous proxy call but does not establish remote cancellation; do not retry an uncertain result. Engine's own internal transport retry behavior remains its responsibility.

The next bounded gate is resolving the remote Python 3.15.2 build environment, then running the packaged synthetic read tool and selected model with correlated live trace evidence and a denied-tool control. It must preserve Engine ownership, trusted identity and provider configuration. Approval/checkpoint/replay acceptance requires a separate workflow bridge; do not enable write tools until that succeeds.

## Runtime loader and installable package

The installable module is `openai_engine_adapter`, with source in [src/openai_engine_adapter](src/openai_engine_adapter/app.py). [OpenAIEngineApp](src/openai_engine_adapter/app.py) registers remote read-tool definitions in TenantRuntime and supplies a fixed Runner entrypoint. Its `get_agent` participates in Tool Pod model discovery without clearing other model registrations. The provider builder and provider adapter factory must supply the actual Engine BaseLLM implementation; the test doubles are not deployment implementations.

The runtime path uses `EngineBindings.from_runtime`: it compares execution, user, session and workspace IDs against Engine contextvars and reuses the AER-owned tool wrapper and step allocator. The standalone `for_request` constructor remains for isolated contract inspection; it is not used by the loader. AER `message` input translates to the internal text request; terminal events now expose `response`, which the real AER consumer requires. This fixes a gap the earlier standalone ExecutionResult tests did not cover.

```bash
uv lock --project compatibility/openai_engine_adapter \
  --python compatibility/hosted-runtime/.venv/bin/python
uv build --project compatibility/openai_engine_adapter \
  --python compatibility/hosted-runtime/.venv/bin/python \
  --out-dir artifacts/compatibility/adapter-dist
```

The package lock resolved 56 packages without a platform restriction. The hosted test environment lock resolved 55 packages with its existing macOS restriction. The source distribution and wheel built successfully from the sdist using uv_build 0.11.3 on Python 3.15.2. Explicit interpreter selection was necessary because the current uv did not discover the manually provisioned 3.15.2 interpreter automatically. These results do not prove Linux installation or a cloud build.

## Selected provider and remote build evidence

The user selected the existing `gpt-6-luna` agent model. [OpenAIProvider](src/openai_engine_adapter/openai_provider.py) uses OpenAI 3.40.0 Responses API inside the Engine Tool Pod, reading its injected key only during invocation. The Runner still invokes the Engine proxy. Provider client retries are disabled; Engine retains its own retry policy. The provider produces a buffered Engine stream chunk, not live token deltas. It rejects unsupported options, incomplete output and execution from the AER mode. Responses storage is disabled. Sources: [model contract](https://developers.openai.com/api/docs/models/gpt-6-luna) and [function calling](https://developers.openai.com/api/docs/guides/function-calling).

[Invoice app](src/openai_engine_adapter/invoice.py) defines the synthetic `demo-1` invoice (7990 USD minor units) and rejects other IDs. This fixture-scope denial is not application tenant authorization or Engine policy proof. [agent.yaml](agent.yaml) gives only the Tool Pod OPENAI_API_KEY and api.openai.com:443 egress; agent egress is deny_all. The fixture disables its own memory feature, leaving the shared project memory configuration unchanged.

Manifest validation with `--strict`, 22 offline tests, sdist/wheel build and `uv pip check` pass. The HTTP tests exercise actual OpenAI request serialization with in-memory transport; they are not a live model call. The build command initially rejected `framework: custom`; using the accurate `openai-agents` identifier allowed archive upload and build creation. This identifier is accepted by the build pipeline but does not establish official adapter support.

Build `bld_01M621HKZWQ2Q13QCGQM15M7ST` failed in the VM image BUILD phase: uv 0.11.21 could not find Python 3.15.2. Its subsequent generic lockfile warning does not establish a stale lock; local locks/builds pass. PRE_BUILD also printed a nonfatal `/src/agent.yaml` lookup error. The build log says it attempted to honor the lock, while current CI/CD documentation describes VM builds differently; do not claim the installed remote dependency set was verified. Platform dependencies may be supplied at platform versions, so remote version checks remain necessary.

Only an explicit source-file allowlist was staged and uploaded, without .env, credentials, caches or artifacts. [Portable evidence](../hosted-invoice-evidence.json) records source hashes: the CLI's Git label points to an older commit, not the exact uploaded local source. No deployment was attempted and independent workspace status remains `not_deployed`. OPENAI_API_KEY was created at workspace scope (version 1), passed via stdin without printing the value; project Anthropic/Grove/Voyage credentials were not changed.

Resolving this gate requires an Engine build image/interpreter path compatible with Python 3.15.2, or a separately authorized change to the Python requirement. This investigation did not establish a supported custom-image/Python-selection field. Do not remove the lock, silently downgrade Python, or report the adapter's live audit/denial acceptance as passed.


## Suspension safety contract

The 25-test hosted-contract suite also verifies that Engine-required model review and tool suspension fail closed when a handler is unavailable: no successful result or fallback tool call is released. A separate event fixture confirms AER preserves opaque suspension metadata. These prerequisites do not implement human approval, checkpoint restoration or replay. The next acceptance gate is specified in [COMP-003](../../docs/tasks/COMP-003-HOSTED.md#approvalresume-prerequisite-contract).


## Experimental review activity

The opt-in `review_invoice:app` entrypoint wraps the read flow with Engine-owned review. The default `invoice:app` remains the bounded read fixture. The first hosted review deployment exposed a rejected direct-suspend contract; the current implementation uses native interruption and Engine step finalization, publishing only the OE-issued activity ID and resume schema. It introduces no approval store or SDK RunState persistence.

The current 49-test suite passes locally on macOS and Linux with real Runner/proxies/AER and doubled OE transport. Bounded hosted suspension, approval, rejection and wrong/stale review-ID controls now pass on deployment `deploy-8e0ea235`; each resumed trace shows one model/tool sequence. Recovery after explicit session sandbox termination also passes. A separate hosted diagnostic confirmed changed-action semantic rejection and stale-attempt-start fencing. The review build was restored afterward; reviewer authorization/expiry and hosted memory continuity remain unvalidated. See [control evidence](../hosted-control-evidence.json). See the [current contract and limitations](../../docs/tasks/COMP-003-HOSTED.md#native-interrupt-correction-after-hosted-rejection) and [exact source/build evidence](../hosted-review-evidence.json). Earlier sections record historical increments, not current deployment status.

## Opt-in review deadline

`expiry_invoice:app` uses workflow version 2 and a 60-second synthetic validity window recorded once by an Engine activity. Hosted timely approval returns the invoice; late approval after sandbox release returns `expired` without invoice data. Deployment `deploy-b0491bde` currently selects this fixture. No-TTL `review_invoice:app` remains version 1; this is not an in-flight migration contract. See [expiry evidence and identity limitations](../hosted-expiry-evidence.json). Independent reviewer authorization and hosted memory continuity remain open.

## Opt-in Engine memory projection

`memory_invoice:app` passes AER's managed memory state to the real Engine proxies and acknowledges non-conversation control activities. Canonical JSON tool output avoids changing memory text during protobuf replay. Deployment `deploy-88907967` currently selects this no-TTL memory fixture. Hosted execution and approval/resume pass; independent persistence/retrieval are not yet validated because the local read token returns 401. The trace memory counter is zero, so it is not positive persistence evidence. See [memory evidence](../hosted-memory-evidence.json). No provider/memory configuration or credential was changed.

After user-managed token refresh, independent read-only checks recovered the hosted marker from STM and from durable memory in a new session; all five user/session filter controls passed without new writes. This supersedes the token/persistence blocker above. Total stored-turn deduplication and automatic model context injection remain open. See [updated evidence](../hosted-memory-evidence.json).
