# COMP-003: Hosted OpenAI Agents SDK execution contract

- Status: Bounded hosted invoice and backend rejection pass; Engine model denial observed; replay, approval/resume and memory continuity remain open
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


## Post-commit hosted verification

Commit `acea824` was independently verified locally with a clean worktree before this evidence update. Deployment `deploy-fbbf9a94` succeeded at 2026-10-28T21:22:57.346Z. A new hosted request in session `phase0-gpt56-invoice-20261028` reached the custom adapter's model operation and was blocked by Engine: `AUTHORIZED_MODELS policy denied model "gpt-5.6-luna" at generation 8` (span `31c6c83011e2c487`). This verifies the deployed model selection and live Engine denial; it does not prove a provider response, tool execution or complete invoice flow.

The project policy still permits only `claude-opus-5-5`. The requested additions of `gpt-5.6-luna` and `lookup_invoice` remain unapplied pending explicit authorization for the shared project permission expansion. No runtime/provider code or shared Anthropic configuration changed in this verification.

## Hosted positive and negative controls pass

Following the user's confirmation to continue after the explicit two-entry permission request, the project policies were updated to append `gpt-5.6-luna` and `lookup_invoice`. Existing Claude authorization, all 26 previous tools and all budgets were preserved. Shared Anthropic memory configuration was not changed. The first two fresh executions still enforced generation 8; a later fresh execution passed after propagation. The documented organization rollout diagnostic returned no delayed projects or pending delivery. No runtime restart or security-control bypass was performed.

[Positive trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-gpt56-allowed3-20261028): execution `109c2502-25d0-46c3-aa39-6bf686e24357` completed an `invoke_llm` step and a `lookup_invoice` step. CLI events and the Engine UI agree on tool call `call_bChc3IzmTfd3IqLnCR23l9nV`. The exact terminal result was `{"invoice_id":"demo-1","amount_minor":7990,"currency":"USD","synthetic":true}`. The UI reported 3.2 seconds and 186 tokens; these are single-request observations, not performance guarantees.

[Backend rejection trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-gpt56-denied-20261028): the model step completed, and `lookup_invoice` rejected `other` with `Synthetic invoice is outside the permitted fixture scope`. The CLI propagated the error and the UI marked the tool step ERROR, with call ID `call_kdT8X47Bim54f2zWaNEQWxbi`. This proves the synthetic backend boundary, not Engine tool-policy denial or tenant authorization. The earlier model-policy denial remains separate evidence.

The basic custom hosted bridge is now proven for this bounded single-call read flow. Approval/resume, replay, hosted memory continuity and broader application acceptance remain open. Geo independently remained ready/healthy at deployment `deploy-e5f6797e`. [Portable evidence](../../compatibility/gpt56-luna-evidence.json) records the controls and limitations. Phase 0 is not complete.

## Approval/resume prerequisite contract

The next bounded gate is Engine-owned suspension and replay, using the pinned SDK/runner 0.11.11 and OpenAI Agents SDK 0.24.0. Official [Engine HITL documentation](https://www.mongodb.com/docs/agentengine/deploy/human-in-the-loop/) describes the LangGraph interrupt/checkpoint integration; it does not provide an OpenAI mapping. Official [OpenAI approval documentation](https://developers.openai.com/cookbook/examples/agents_sdk/migrate-from-claude-agent-sdk/readme#step-7-add-approvals-for-side-effects-with-human-review) exposes interruptions and RunState, but that SDK lifecycle must not become an independent approval owner under ADR-0018.

Pinned source inspection identifies these extension boundaries:

- `SecureToolWrapper._handle_suspend` validates the Engine-confirmed SuspendPayload and calls the registered native or durable suspend handler. Without one, it raises; returning a human-decision dictionary alone is not a checkpoint implementation.
- `SecureLLMProxy._handle_require_review` fails closed without a suspend handler. A tool approval and a model-output guardrail review use different payloads and must not share an unchecked decision parser.
- AER consumes a terminal `suspend` StreamEvent and preserves its `metadata` in InterruptResult. On resume, AER places platform resume information in `RequestContext.resume`, `resume_data` and `metadata`, not the caller payload. A copied envelope proves neither persistence nor authorization.
- Registering a workflow adapter only advertises an identity and enables durable attempt routing; it does not implement activity replay. No such hook is registered by this adapter.

Three new deterministic tests exercise the real pinned Engine handlers/AER with transport or event fixtures: model review prevents tool execution; tool suspension emits no success event and does not retry; AER preserves opaque suspension metadata. Existing tests reject resume/recovery metadata before any bindings or model/tool calls. All 25 hosted-contract tests pass on Python 3.15.2 macOS ARM64 and Linux/amd64 under Docker Desktop emulation. These are local contracts, not live human approval or replay acceptance. Application code, remote deployments and policies were not changed for this increment.

### Next implementation acceptance

Implement one synthetic review with no business side effects, only after identifying the Engine-owned checkpoint/replay path. Bind the pending action to execution, authenticated identity, workspace, tool call ID and exact arguments. Validate approval and rejection, reject a stale or mismatched decision, and resume in a fresh process with prior Engine activities served from recorded results. Verify no additional provider/tool call for completed activities and no success after rejection. Preserve model guardrail review as a separate contract. Do not add an application approval database, enable SDK approval as a competing owner, or register a placeholder workflow adapter to bypass this gate.


## Engine-owned review activity prototype

[review.py](../../compatibility/openai_engine_adapter/src/openai_engine_adapter/review.py) now implements an isolated review activity using the pinned Engine `run_serial_activity` primitive. It requires an active Engine attempt, verifies execution/session/workspace identity, includes the requesting user and exact tool name/call ID/arguments in semantic input, and leaves activity identity, hashing, outcome storage and replay with OE. The initial prototype raised `DurableActivitySuspended`; hosted OE subsequently rejected that path (see the native-interrupt correction below). A recorded completed answer returns a strict approve/reject decision without reporting another outcome. Unknown outcomes use the Engine `fail` policy, with no adapter retry or second outcome report.

Six new tests use the real Engine activity helper and protobuf contracts with signature-checked OE transport doubles: initial wait recording, fresh-attempt approval/rejection replay without redispatch, recorded policy denial, ambiguous suspension delivery, missing/mismatched attempt identity and malformed recorded decisions. All 31 hosted-contract tests pass on Python 3.15.2 macOS ARM64 and Linux/amd64 emulation. Linux uses the previously validated dependency image with current source mounted read-only; no new hosted image was built. Tests do not measure live OE persistence, stale-fence enforcement, action-hash mismatch rejection or fresh-process recovery.

The prototype is not registered in `invoice:app` and introduces no workflow/suspend hook, external store or new policy permission. It does not deserialize SDK RunState or trust an approval from invocation input. A returned decision alone never authorizes a business write; current eligibility, expiry, reviewer authorization and idempotency still require the completed integration and backend checks.

Next gate: wire AER attempt/step finalization, a versioned state snapshot and OE resume routing to this primitive; verify model/tool replay and decision-to-action binding in a restarted runtime. Do not enable this prototype in the hosted invoice until those contracts pass. The absence of a competing memory/approval owner is preserved; Phase 0 remains open.

## AER review lifecycle bridge

[review_execution.py](../../compatibility/openai_engine_adapter/src/openai_engine_adapter/review_execution.py) now provides an opt-in AER stream around the bounded read adapter. It requires an Engine-issued attempt and matching execution/session/workspace identity before running the read. It reconstructs the read flow on replay, obtains the review answer only from the Engine activity outcome, and emits an empty-metadata suspension envelope only after the Engine helper acknowledges the wait. It does not deserialize SDK RunState from caller input.

On approval, the bridge releases the original validated read result; on rejection, it returns a fixed JSON rejection without invoice data. Before either terminal result is emitted, the actual Engine `settle_execution` helper finalizes the current step and completes the execution with the same StateSnapshot and fence. Ambiguous wait delivery, invalid resume context and failed completion propagate as errors without a success event. Inline resume data does not override a recorded rejection.

To resolve the lifecycle contract, the official agent-engine-sdk-langgraph 0.11.11 wheel was downloaded for source inspection only and checked against PyPI SHA-256 `2c86a61e8301da22b651775b923edd933840db3d0162011cc28855381452bdcd`. It was not installed as an application dependency. Its direct DurableActivitySuspended path confirms that an acknowledged wait is followed by an AER suspend event, whereas native framework interrupts use a different finalization path. This was the initial implementation hypothesis, later disproved by the hosted rejection below. The corrected bridge uses native interrupt finalization.

Five new tests run this bridge through the real AER parser and real activity/settlement helpers with doubled OE clients. They cover suspension, approval/rejection, uncertain wait delivery, failed completion and invalid attempt/resume context. The suite now has 36 tests. A fresh AttemptContext in a test is not an actual process restart or a live OE recovery proof. The wrapped read is doubled in lifecycle tests, so absence of repeated model/tool work still needs an integrated test using the real proxies and live Engine outcomes.

This bridge remains outside the deployed `invoice:app`. Before enabling it: integrate the versioned workflow declaration and real read proxies; establish the Engine resume-map/activity resolution and state-encoding contracts in a hosted synthetic run; test fresh-process restoration, changed-action rejection and stale fences. No hosted image, policy or memory setting changed in this increment. Phase 0 remains open.

## Durable entrypoint and integrated proxy replay

The opt-in `review_action_factory` on OpenAIEngineApp wraps the real read agent and registers the implemented `openai-engine-review/1` workflow declaration. [review_invoice.py](../../compatibility/openai_engine_adapter/src/openai_engine_adapter/review_invoice.py) validates the invoice result and requests review before release; it performs no business writes. The original `invoice:app` entrypoint and its manifest remain available. The staged review manifest selects `review_invoice:app` for the bounded hosted experiment.

A new integrated test uses the actual Runner, SecureLLMProxy, SecureToolWrapper, Engine activity helpers and AER parser. It reconstructs the app and proxies with a new attempt and serialized fake OE outcomes. It observes stable activity positions 1/2/3 for model/tool/review, exactly one underlying model dispatch and one tool dispatch across both legs, and a completed invoice only after Engine settlement. This proves the client integration with replay responses, not server-side persistence, fencing or an OS-process restart. All 37 tests pass on macOS and the freshly built Linux/amd64 image.

Remote build `bld_01M628TVC2X3R06QT2YDWYJ1RA` was started from the verified compact Python bundle and the staged review entrypoint. [Review evidence](../../compatibility/hosted-review-evidence.json) records exact source hashes separately from the CLI Git label and will track hosted outcomes. No new tool permission or shared memory change was introduced by this build.

## Native interrupt correction after hosted rejection

The first review build `bld_01M628TVC2X3R06QT2YDWYJ1RA` and deployment `deploy-69e4df59` succeeded, but session `phase0-review-approve-20261028` failed: `invalid workflow input: app.suspend() is not supported; use the framework's native interrupt instead`. Local transport doubles had accepted an outcome the live OE forbids. Earlier direct-wait descriptions are historical, not supported contracts.

The corrected bridge raises an adapter-native `ReviewInterrupt` through Engine's `DurableActivityInterrupted`. Engine records the exact interrupted ActivityCommand without reporting a direct suspended outcome. The bridge finalizes that position with `StepSuspensionEntry`, reason `agent_interrupt` and context `{"value": ...}`, following the pinned official LangGraph adapter's `durable_session.py` contract without installing LangGraph. Only an acknowledged canonical frontier supplies the public activity ID and `resume_map` schema. Empty or mismatched frontiers fail closed. If finalization returns an already resolved answer, the bridge validates it and settles the result instead of publishing an obsolete wait.

All 39 local contract tests pass on Python 3.15.2 macOS ARM64 and the fresh Linux/amd64 image `telecom-review-v2:local`. They assert no direct suspended outcome report, exact native reason, OE-issued resume ID, failure on unknown finalization, and resolution during finalization. The integrated replay test retains real Runner/proxies/AER and explicitly doubled OE transport; it is not live persistence or fencing evidence. Build `bld_01M629GDVMFFAKH5SXYKMVMVFV` stages the corrected source; current remote outcomes and exact hashes are recorded in [review evidence](../../compatibility/hosted-review-evidence.json). Hosted approval/rejection, resumed replay, changed-action/stale-fence controls and memory continuity remain acceptance gates. Shared Anthropic settings are unchanged.

## Hosted native review and resume pass

Corrected build `bld_01M629GDVMFFAKH5SXYKMVMVFV` and deployment `deploy-8e0ea235` succeeded; rollout completed at 2026-10-28T22:23:57.324Z. The CLI uploaded locally authored, uncommitted source; its Git label is not proof that these changes were committed.

- [Approval trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-review-v2-approve-20261028): execution `ea049029-a799-4daa-9cb0-a43cd4a49bb8` first returned two completed activities and suspended review `6ae27608f09e1404c0919f53`, together with the exact action and resume schema. Resuming that ID with `{"decision":"approve"}` returned the exact validated synthetic invoice in the same execution. The UI shows one run, one `invoke_llm`, one `lookup_invoice` and one successful Human review; 245 tokens.
- [Rejection trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-review-v2-reject-20261028): execution `3426a442-8132-4615-a626-041fe31c12de`, review `6ae2761c0a7e41e68bf9ec93`, returned exactly `{"status":"rejected","tool_call_id":"release-demo-1"}` after rejection. The UI shows one run and one model/tool/review sequence; 234 tokens.
- Submitting the approval session's review ID to the waiting rejection session failed with `RESUME_INPUT_INVALID`. A valid rejection still succeeded afterward. Submitting a late approval to that completed rejected session also failed with `RESUME_INPUT_INVALID`.

This proves bounded hosted native suspension, approve/reject resumption and rejection of wrong/stale review IDs. No duplicate model/tool steps are visible across either resumed run; independent provider billing counters and a forced process restart were not tested. It does not prove changed-action semantic hash rejection, stale attempt fencing, reviewer delegation/expiry, business writes or hosted memory continuity. These remain explicit acceptance gaps; Phase 0 is still open. [Portable review evidence](../../compatibility/hosted-review-evidence.json) contains the controls and source hashes. Shared Anthropic memory settings and the default read manifest remain unchanged.

## Recovery after explicit session sandbox termination

Using the unchanged validated deployment `deploy-8e0ea235`, session `phase0-review-restart-20261028` suspended execution `8e5dc5b4-aad0-4380-8956-b1301e6c5561` at review `6ae276e70a7e41e68bf9eca4`. The CLI's `workspace sessions stop` command explicitly destroys reserved agent/tool sandboxes and ephemeral process/filesystem state while preserving history. Stop returned `stop_accepted`; a subsequent full session list contained only the two earlier approve/reject sessions, confirming release before resume.

A resume answer containing extra `arguments: {"amount_minor": 1}` failed with `RESUME_INPUT_INVALID`. A subsequent valid `{"decision":"approve"}` succeeded and returned the unchanged synthetic invoice in the original execution. The [post-recovery trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-review-restart-20261028) shows one run, one model call, one invoice tool and one human review, with 227 tokens. This is hosted recovery after sandbox termination at a durable wait, beyond fresh-object local replay. It does not test a crash during a tool's uncertain external outcome or independent provider billing counts.

The suite now has 41 passing tests on macOS Python 3.15.2 and the existing Linux/amd64 image. New tests confirm that Engine `CONFLICT` and `STALE_FENCE` errors propagate without retry/fallback, and that changes to tool name, call ID or arguments change the semantic input sent to OE at the same activity position. These use doubled OE replies: live stale-fence enforcement and server-side changed-action hash rejection remain unvalidated. Rejecting extra arguments in a public resume answer proves schema enforcement, not that latter semantic comparison.

Reproduction uses the explicit workspace/project/org/base URL flags from the prior deployment commands: invoke a unique synthetic session, capture the returned interrupt ID, run `agentengine workspace sessions stop <session>`, verify that session is absent from `workspace sessions list --json`, then invoke `--resume '{"<interrupt-id>":{"decision":"approve"}}' --session <session>`. Never infer release from `stop_accepted` alone. This increment changed tests/evidence only; it did not rebuild, change policies/memory, or commit. Phase 0 remains open for live action/fence controls, reviewer authorization/expiry and hosted memory continuity.

## Dedicated OE conflict and fencing diagnostic

The opt-in [contract_probe.py](../../compatibility/openai_engine_adapter/src/openai_engine_adapter/contract_probe.py) entrypoint adds one harmless Engine activity before the existing invoice/review fixture. It persists the original owning attempt/fence only in that activity's Engine result. Three requests reuse the activity position with altered action arguments, call ID or tool name and must receive `NONDETERMINISTIC`. On a resumed attempt, the fixture requires a newer fence and submits the exact original lease, expecting `STALE_FENCE`. Unexpected acceptance or an unrelated/unknown error fails the experiment; no mutation dispatch or fallback executes. Logs contain only fixed control labels/statuses, not leases, credentials or identities.

This is a diagnostic entrypoint, not production approval logic. Default `invoice:app` and `review_invoice:app` do not invoke the probe. The 45-test suite passes on Python 3.15.2 macOS and Linux/amd64 emulation; new tests validate the diagnostic's failure behavior and exact stale lease request with doubled transport. [Control evidence](../../compatibility/hosted-control-evidence.json) records exact staged source hashes and remote outcomes separately. A successful control concerns OE activity replay identity, not current business eligibility, reviewer rights, expiry, or transaction idempotency.

The initial diagnostic deployment `deploy-87302f61` became healthy after the Atlas interruption. Session `phase0-oe-controls-20261029` rejected the changed activity with `workflow is nondeterministic`. The fixture initially expected generic `CONFLICT` and therefore failed closed before the remaining controls. Its expectation is corrected to the pinned `NONDETERMINISTIC` enum; this is not a relaxation to accepting arbitrary errors. The corrected 45-test macOS suite passes; the fresh image and hosted rerun are tracked in control evidence.

## Hosted action identity and stale attempt controls pass

Corrected build `bld_01M62MK5ZBC56973ABV9QBDT4P` deployed successfully as `deploy-38e1d8dc` at 2026-10-29T01:37:12.334Z. [Session trace](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-oe-controls-v2-20261029) identifies execution `72f74cb7-8bcd-4620-baa5-3cf32b0078ef`. The first attempt completed the control activity, model and tool, then suspended review `6ae2a371f09e1404c0919f8f`.

The correlated hosted log at 01:37:49.841Z confirms three rejected semantic-input changes at the original activity position: invoice arguments, tool call ID and tool name. The fixture requires the exact `NONDETERMINISTIC` code. After approval, a newer Engine attempt replayed the original recorded lease and submitted that old attempt/fence back to OE. The correlated resume log at 01:38:02.535Z confirms all three semantic rejections again plus `stale_attempt: rejected`, which requires `STALE_FENCE`. The same execution completed with the exact original synthetic invoice. The resume log appeared later in the log query than the terminal result; no success was inferred from an initially missing log.

This establishes the bounded live activity-identity and stale-attempt-start controls. It does not cover stale outcome reports, concurrent writers, lease expiry during a tool, reviewer authorization/expiry or business idempotency. [Portable control evidence](../../compatibility/hosted-control-evidence.json) records source hashes, failed initial expectation, both correlated logs and limitations.

After the experiment, build `bld_01M629GDVMFFAKH5SXYKMVMVFV` (`review_invoice:app`, without the diagnostic) was restored by successful healthy deployment `deploy-72088429` at 01:39:12.32Z. Shared Anthropic memory, policies and the default source manifest were unchanged. The corrected 45-test suite passes on macOS and the newly built Linux/amd64 image. Changes remain locally authored and uncommitted; Phase 0 remains open for the remaining authorization/lifecycle and hosted memory gates.

## Review identity boundary and expiration implementation

Pinned `RequestContext` exposes execution/session/user/workspace and resume plumbing, but no distinct authenticated reviewer assertion or decision timestamp. A live invocation using the current CLI credential with `--user-id synthetic-unprivileged-reviewer` succeeded, carrying that delegated value into the review semantic input. The session was closed by rejection under the same delegated value. This is not a login as a second low-privilege identity and does not establish reviewer authorization or a bypass. An independent negative reviewer test requires a separate test identity with known permissions; none was created or granted privileges by this increment.

The opt-in `expiry_invoice:app` fixture uses workflow declaration `openai-engine-review/2` and a synthetic 60-second TTL. A separate Engine activity records the issue/deadline once, with exact action, requester and TTL in semantic input. Replays restore the deadline without consulting the clock again for issuance. The review includes that recorded deadline in its semantic input and visible interrupt value. After an Engine-recorded approval, backend time validation returns exactly `{"status":"expired","tool_call_id":"release-demo-1"}` at or after the deadline, before settling a result. Rejection remains rejection. There is no competing approval store or timer service. This does not automatically close an unanswered Engine wait; it validates eligibility when processing its decision, using runtime wall-clock time.

The existing no-TTL review fixture keeps workflow version 1; switching between versions is not an in-flight migration contract. The 48-test suite passes on macOS Python 3.15.2 and a fresh Linux/amd64 image. Added tests cover the exact expiry boundary, approval before the boundary, and replay without deadline renewal. [Expiry evidence](../../compatibility/hosted-expiry-evidence.json) tracks exact source/build provenance and the separate hosted controls. A production TTL and reviewer authorization policy remain domain decisions, not defaults established by this 60-second experiment.

## Hosted review expiry and restart preservation pass

Build `bld_01M63Q77KBGH3BD6F4YK54Z040` and deployment `deploy-b0491bde` succeeded; rollout completed at 2026-10-29T11:42:14.048Z. The active fixture is `expiry_invoice:app`, workflow version 2, with a synthetic 60-second validity window.

- [Within-deadline control](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-expiry-valid-20261029): execution `06200ef7-856f-441b-9ce0-b96fe41061f1` suspended with its persisted deadline and returned the exact original synthetic invoice after timely approval.
- [Expired recovery control](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-expiry-late-20261029): execution `425466f2-7d45-4eec-aa2c-1a18cb2bd2f7` issued deadline 1793274253.1134074. Its sandboxes were stopped and the session disappeared from the full runtime session list. After that deadline, approval resumed the same execution and returned exactly `{"status":"expired","tool_call_id":"release-demo-1"}`, without invoice data. Recovery therefore did not renew the validity window.

The Engine accepts and persists the review decision; backend code determines whether its result remains eligible for release. This is not automatic wait cancellation or independent reviewer authorization. The current caller could delegate a synthetic `user_id`; a second identity with known permissions is still needed for the independent negative authorization test. No new account, permission, credential or shared Anthropic configuration was created or changed. [Expiry evidence](../../compatibility/hosted-expiry-evidence.json) contains exact source hashes and observed outputs. The 48 local tests pass on macOS/Linux; the repository checks and diff whitespace checks pass. The phase remains open for reviewer authorization, broader failure modes and hosted memory continuity.

## Opt-in hosted memory projection

The `memory_invoice:app` fixture uses explicit `managed_memory=True`, workflow adapter version 3 and a staged manifest with `features.memory: true`. The default manifests remain unchanged. AER creates the Engine `DurableMemoryState`; the adapter passes that same instance to SecureLLMProxy and keeps AER's SecureToolWrapper. Missing memory-enabled durable context fails closed. Engine's own projection/write protocol owns user, assistant/tool-call and tool-result records. Review/deadline controls acknowledge empty memory batches, including the resolved-at-finalization race; they do not become conversation turns.

A real-proxy replay test exposed a pinned 0.11.11 projection issue: dict-to-string tool memory text changed with protobuf field ordering/number conversion on replay. The adapter's memory mode now transports validated canonical JSON strings from the Tool Pod and validates them again at the SDK boundary. Engine projects the same string on both attempts. No Engine internals or managed collections were patched.

All 49 tests pass on macOS Python 3.15.2 and a fresh Linux/amd64 image. The integrated test confirms identical replay content and three stable write IDs, with no provider/tool redispatch and an empty review acknowledgement. Transport is doubled: this alone does not establish hosted writes, deduplication or retrieval. [Hosted memory evidence](../../compatibility/hosted-memory-evidence.json) records source hashes and live outcomes separately. Shared Anthropic credentials, model and memory-server settings remain unchanged. Model history reconstruction/retrieval injection is not implemented by this projection-only increment.

## Hosted memory-enabled execution passes; retrieval gate remains open

Build `bld_01M63VC2WBEK836XZFFZK2HEAJ` deployed as `deploy-88907967`, completing at 2026-10-29T12:58:37.333Z after internal certificate/OE rollout readiness recovered. `agentengine memory status` reports ready. [Synthetic session](https://agentengine.mongodb.com/project/67b385a7976edf15ecc62e06/sessions/phase0-session-98751e7966484cf3a7703be3086aa820), execution `868b633d-03e4-486c-93ef-a560f8621fca`, completed the model/tool flow, suspended and resumed approval successfully with the memory-enabled adapter. The user message contains `SYNTHETIC-PROBE-98751e7966484cf3a7703be3086aa820` for a later independent query. No standalone SDK turn writer was used.

The trace shows one model/tool/review sequence, 246 tokens and zero UI memory saves/recalls. The marker was not found in the memory UI's 40 loaded long-term records; that client-side filter is not an exhaustive persistence query. Neither observation justifies claiming stored/retrievable memory or deduplication. The independent read-only `engine-context` preflight returned `MemoryAuthError`, `INVALID_TOKEN`, HTTP 401 at 2026-10-29T12:52:02.492193+00:00 using the existing local service token. No credential was overwritten. A valid token for the same project is required to complete the existing read-only diagnostic:

```bash
uv run --project compatibility/agent-runtime --frozen --env-file .env \
  python scripts/check_memory_isolation.py \
  --run-id 98751e7966484cf3a7703be3086aa820 --allow-live \
  --output artifacts/compatibility/hosted-memory-isolation.json
```

Do not create another marker or write a duplicate turn to compensate for failed retrieval. Persisted STM, negative filters, managed promotion and new-session durable retrieval must be observed separately. The current hosted fixture enables memory projection and no-TTL review; expiry plus projection has not been live-tested together. Model context retrieval/history reconstruction still requires implementation. The 49-test macOS/Linux suite and repository checks pass. Phase 0 remains incomplete; locally authored changes are uncommitted.

## Independent hosted-memory retrieval passes after token refresh

After the user refreshed the existing local token, the frozen Python 3.15.2 `engine-context` read-only preflight passed at 2026-10-29T13:03:44.712842+00:00. The existing `check_memory_isolation.py` probe reused run ID `98751e7966484cf3a7703be3086aa820`; no new turns, promotion requests or configuration changes were issued.

At 13:04:00.869173+00:00 all five checks passed: the exact hosted marker was found in same-session STM; changing only session or only user excluded it from STM; semantic/episodic context recovered it for the same user in a new session with STM excluded; a different user did not retrieve that durable marker. Every requested source reported healthy hybrid retrieval without retryable/degraded outcomes. [Hosted memory evidence](../../compatibility/hosted-memory-evidence.json) embeds the sanitized report.

This independently establishes persistence and new-session durable retrieval of the marker written through the hosted adapter, superseding the earlier token blocker and inconclusive zero UI memory counter. It does not prove the total stored-turn count/deduplication, independent tenant authorization, or automatic injection into the OpenAI Runner's context. Those remain separate; Phase 0 is not complete. Anthropic configuration and client credentials were not modified by the assistant, and no token value is recorded in evidence.
