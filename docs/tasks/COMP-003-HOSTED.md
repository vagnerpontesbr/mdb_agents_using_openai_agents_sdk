# COMP-003: Hosted OpenAI Agents SDK execution contract

- Status: Local macOS/Linux contracts and remote VM build pass with bundled Python 3.15.2; deployment succeeded; live model call blocked by project policy; invoice execution unverified
- Owner: Repository implementation
- Dependencies: COMP-001, existing agentsdk workspace, provider access
- Relevant ADRs: [Two-cluster boundary](../adr/0017-two-cluster-memory-boundary.md)

## Scope

Prove a minimal OpenAI Agents SDK workflow through the Engine hosted runtime, preserving OpenAI orchestration. Memory-only compatibility is separate. Do not substitute LangGraph/ADK or treat workspace framework metadata as an executable adapter.

## Acceptance criteria

- Identify and pin an actual adapter/runner contract before packaging.
- Run one synthetic tool-backed request with correlated model/tool audit evidence.
- Validate replay and approval/interruption resume separately from basic execution.
- Record unsupported framework, Python/platform or provider contracts explicitly.
- Preserve the shared memory project, existing geo deployment and dedicated agentsdk workspace.

## Validation plan

Inspect official framework and runner APIs, then test the smallest local adapter contract before any hosted build. Use the chosen Python target without silent downgrade. Add real dependency locks and tests with implementation. A successful local Python Runner call is not a hosted execution proof.

## Evidence and handoff

On 2026-10-28, CLI 0.1.120 help confirmed that build requires a local agent source directory; a workspace ID alone is insufficient. The [official SDK overview](https://www.mongodb.com/docs/agentengine/sdk/) lists LangGraph (Python/TypeScript) and Google ADK (Python), not OpenAI Agents SDK. The [base SDK API](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk/docs/api/) documents BaseApp, BaseAgent.execute and an awaitable/async-iterable ExecutionResult. Runtime tool_wrapper and llm_wrapper injection are part of that integration boundary. These are extension contracts, not a ready or tested OpenAI implementation.

The locked local agent environment currently installs openai-agents 0.24.0 and agent-engine-sdk-memory 0.11.11; it does not install the Engine base runner/adapter. No hosted build or deployment was attempted. The next deliverable is a bounded adapter/runner feasibility check covering tool/model routing and interruption semantics; package names and versions must be verified rather than inferred. A custom adapter, if needed, requires an explicit documented design and compatibility proof before any support claim.


## Pinned runner contract experiment

On 2026-10-28, official PyPI wheels for agent-engine-sdk and agent-engine-runner-shared 0.11.11 were downloaded and checked against their published SHA-256 digests. The [Python SDK catalog](https://www.mongodb.com/docs/agentengine/sdk/python/) identifies these as internal core packages rather than application-facing framework adapters. They are used here only in an explicitly isolated compatibility experiment.

[The hosted diagnostic environment](../../compatibility/hosted-runtime/pyproject.toml) pins both Engine packages and openai-agents 0.24.0 on Python 3.15.2. `uv lock` resolved 54 packages and frozen `uv sync` installed 53 packages on macOS ARM64, including a local PyYAML build. The validated [lock](../../compatibility/hosted-runtime/uv.lock) is versioned. Existing agent/ingestion environments were not modified. This environment is not an application package and has no build target. Linux/container compatibility remains untested.

[check_hosted_contract.py](../../scripts/check_hosted_contract.py) imports the real pinned packages without creating a runtime. It invokes the real TenantRuntime.get_agent dispatch guard with a minimal synthetic object holding the native OpenAI Agent. The call is rejected because the Agent lacks get_agent(). The object also fails the Engine BaseAgent structural protocol, and model, workflow and suspend hooks remain unregistered. The diagnostic returned exit 2: inspection assertions passed, but native hosted integration remains blocked. This is a negative contract proof, not an adapter test or hosted acceptance.

```bash
uv sync --project compatibility/hosted-runtime --frozen
uv run --project compatibility/hosted-runtime --frozen \
  python scripts/check_hosted_contract.py \
  --output artifacts/compatibility/hosted-contract.json
```

[Portable evidence](../../compatibility/hosted-contract-evidence.json) includes tested versions, hashes and outcomes. The runner constructor, network servers, provider calls and remote build/deploy were not executed. The launcher accepting a callable entrypoint is not proof that the resulting application implements the Engine execution contract.

## Required adapter work before a hosted claim

| Concern | Required mapping | Current evidence |
|---|---|---|
| Application loading | BaseApp/get_agent to a BaseAgent wrapper | Custom App accepted by actual runtime dispatch; native Agent remains rejected |
| Execution | Engine input/output and awaitable/streamed ExecutionResult to OpenAI Runner | Custom single-read flow passes real AER result parser locally with doubled transport |
| Models and tools | Engine wrappers/proxies to SDK model and function-tool calls | No adapter factory registered; direct SDK calls do not prove Engine audit/policy enforcement |
| Human review | SDK interruptions/RunState to Engine suspend/resume payload and exact pending action | Not implemented or tested |
| Durable execution | Registered workflow adapter, stable activity identity and replay behavior | No workflow adapter registered |
| Memory ownership | Engine-managed persistence without duplicate application writes | Separate memory API proof passes; hosted adapter integration remains open |

The user stopped the proposed adapter prototype before implementation. The [Engine precedence decision](../adr/0018-engine-feature-precedence.md) now governs this task: Engine owns overlapping platform features; any future bridge only translates SDK orchestration to those capabilities. No parallel approval, replay, policy, memory or primary tracing implementation is authorized by the earlier prototype proposal. Before resuming implementation, scope one Engine-mediated contract and its live acceptance criteria under this matrix. The existing negative diagnostic remains valid evidence; this review adds no adapter or hosted acceptance.

## Custom adapter implementation after ownership review

The user explicitly authorized a custom adapter after ADR-0018. [Implementation and usage](../../compatibility/openai_engine_adapter/README.md) now provide OpenAIEngineAgent, a request-local EngineBindings factory and strict remote read-tool registrations. The adapter uses the real Runner and the pinned Engine BaseAgent/ExecutionResult/model/tool contracts. It emits one terminal event, preserves call IDs, disables SDK trace export and adds no memory/replay/approval owner.

Eleven tests passed in the frozen Python 3.15.2 macOS ARM64 environment: real Runner flow through signature-checked transport doubles, text-only output, denied tool and model timeout failure, malformed call rejection, strict result rejection, input/context boundaries, single-use results, copied context, concurrent runs and real proxy construction with a shared step allocator. No provider/OE calls occurred. This supersedes the earlier stopped-prototype status, not the negative native integration evidence.

Next gate: integrate the actual runtime loader and provision a synthetic remote read tool, then prove correlated live model/tool traces and a denied action. Resume, replay, memory continuity, Linux and hosted acceptance remain open.

## Loader and packaging increment

The custom BaseApp now registers remote read tools and supplies get_agent/run. Runtime bindings reuse the AER context wrapper instead of replacing it, validating execution/user/session/workspace identity and preserving the shared operational-step allocator. Actual AER input/output inspection exposed two earlier local gaps: normalized `message` input and terminal `response` output. Both now have tests against the real dispatch/stream consumer.

Sixteen adapter/loader tests pass. A source distribution and wheel build pass on Python 3.15.2 with explicit interpreter selection; the installable package and hosted test environment have updated uv locks. The original build invocation failed to discover the manually provisioned interpreter; no Python target was downgraded. Linux execution is not inferred from the unrestricted package lock.

Read-only workspace status confirms `not_deployed`. Provider selection for the invoice Tool Pod is pending clarification (Anthropic/Grove versus configured OPENAI_MODEL); shared Anthropic memory is preserved. A concrete provider adapter, remote image/tool provisioning, live correlated traces and a real denied-policy control remain required. No remote build/deploy or policy/secret mutation occurred in this increment.

## OpenAI provider selected; remote build blocked

The user authorized retaining gpt-6-luna. The concrete provider now implements Engine BaseLLM using OpenAI 3.40.0 Responses API from the Tool Pod. The synthetic invoice app and sandbox manifest are implemented. Twenty-two local tests, strict manifest validation, dependency checks and sdist/wheel build pass. Tool Pod secret injection and model/tool proxy ownership remain separate from shared Anthropic memory.

The build pipeline rejected `python-custom`, then accepted `python-openai-agents`. Build `bld_01M621HKZWQ2Q13QCGQM15M7ST` was started with an allowlisted source archive and failed in BUILD: the platform uv could not find Python 3.15.2. The later generic lock warning is not evidence that regenerating the local lock fixes this interpreter error. No Python downgrade or lock removal was attempted. The independent workspace status remains not_deployed.

OPENAI_API_KEY was created only in the agentsdk workspace and independently listed at version 1; no secret values were logged and project memory/provider settings were preserved. [Portable evidence](../../compatibility/hosted-invoice-evidence.json) records build identity, root/secondary errors and the hashes of the actual locally authored uploaded source. The CLI commit label must not be treated as the uploaded source revision.

Next: resolve the remote interpreter/base-image contract while preserving the Python target, then build/deploy and measure live model/tool correlation and Engine denial. There is no live invoice or platform-policy proof yet. A concrete hosted blocker, not provider selection, now prevents this acceptance gate.

## Bundled Python follow-up

The [Python 3.15.2 build experiment](../compatibility/PYTHON315_HOSTED.md) resolves interpreter discovery without changing the version or removing the lock. Full and compact runtime profiles both passed frozen Linux/amd64 installation and 22 offline adapter tests. The full archive was rejected by the platform decompressed-size limit. The compact profile (about 49 MB of regular files) was accepted and build `bld_01M622CNYJW9R30TVZQ0Q36DQF` succeeded, including the Firecracker image push. This supersedes the original missing-interpreter blocker; it does not establish generic Python distribution support.

Deployment `deploy-f45c6a70` was initiated for that exact build in agentsdk. Live invoice/denial and runtime readiness remain separate gates. Forty-six bootstrap compatibility tests, including staging exclusion/checksum controls, pass. [Portable follow-up evidence](../../compatibility/python315-linux-evidence.json) records source hashes, interpreter provenance and remote outcome.


## Live deployment and policy diagnosis

Deployment `deploy-f45c6a70` completed successfully at 2026-10-28T20:28:52.331Z. The earlier OE/certificate readiness conditions resolved. Runtime logs confirm AER warm-up, `lookup_invoice` registration and named LLM discovery.

The blocking invocation returned HTTP 500. A separate streaming invocation created [session ed893800-3d15-4a29-b0e7-4a00af611273](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/ed893800-3d15-4a29-b0e7-4a00af611273). Its `invoke_llm` step (span `8a13e9ae9aa61331`) is BLOCKED with `AUTHORIZED_MODELS policy denied model "gpt-6-luna" at generation 8`. The UI and CLI agree on denial. No provider response or invoice result was obtained.

Read-only policy inspection confirms the project permits only `claude-opus-5-5`; the 26 authorized tools do not include `lookup_invoice`. These policies apply to every workspace, including geo-intelligence-network. The concrete proposed correction is to append `gpt-6-luna` and `lookup_invoice` to their respective lists, retaining all existing values and budgets. This broadens shared project permissions and awaits explicit approval. It does not change the shared memory model or its credentials. No policy was saved.

After approval: verify effective policies, retry the synthetic positive control, correlate model/tool traces and test the backend rejection of an out-of-fixture invoice. Preserve the observed Engine model denial separately; a backend PermissionError is not Engine policy evidence. Approval/resume, replay and memory continuity remain unimplemented. Phase 0 is incomplete.


## User-selected GPT-5.6 Luna follow-up

The latest user instruction selects `gpt-5.6-luna`, superseding `gpt-6-luna` for future invoice runs. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna) confirms Responses and function calling. A single direct provider call on Python 3.15.2 completed and returned exactly `lookup_invoice({"invoice_id":"demo-1"})`, using 149 input and 21 output tokens. [Evidence](../../compatibility/gpt56-luna-evidence.json) records the request outcome. This provider-only test did not execute the tool or route through Engine.

Local provider defaults, invoice registration and HTTP contract expectations now use `gpt-5.6-luna`. The existing image and its source hashes remain historical and unchanged. The pending shared-policy proposal is now to append `gpt-5.6-luna` (not `gpt-6-luna`) and `lookup_invoice`, retaining all existing entries and limits. Approval, new staging/build/deploy, the hosted positive control and backend denial test remain pending. Shared Anthropic memory is unchanged.


## GPT-5.6 Luna image preparation

The updated source passed frozen Linux/amd64 installation and all 22 adapter/loader/provider tests with the bundled Python 3.15.2 interpreter. Build `bld_01M6262645YTMRR5FQX2CH2JJY` uploaded the fresh allowlisted 17.1 MB source archive and entered `in_progress`. [Model evidence](../../compatibility/gpt56-luna-evidence.json) records the new source hashes separately from the previous deployed image. The shared policy expansion was presented for explicit approval; no policy changes have been applied at this checkpoint.

Build `bld_01M6262645YTMRR5FQX2CH2JJY` subsequently succeeded. Deployment `deploy-fbbf9a94` was started for that exact build in agentsdk. Runtime readiness and the shared-policy approval remain pending; this is not a hosted invoice acceptance.
