# LANG-2 hosted rollout proposal

Status: requester approved cancellation, remote build/deployment and the bounded
live evaluation with "sim autorizo" on 2026-11-01. Drain, rollout and all hosted/HTTP acceptance gates passed; Git integration pending. Authority: [I18N-001](../tasks/I18N-001-MULTILINGUAL.md).

## Exact target and source

- Project: 67b385a7976edf15ecc62e06; workspace: agentsdk,
  ws-6ae20f53f3b040aa65fa961a.
- Current deployment: deploy-af009ed4; rollback build:
  bld_01M691YPABN60FEKHW6E1KZGB5.
- Entrypoint remains openai_engine_adapter.knowledge_review:app. Workflow
  telecom-journey changes from version 8 to version 9 for locale/tool semantics.
- Stage: /tmp/telecom-lang2c-workflow9. The exact source-tree hash, per-source hashes,
  interpreter and size proof are in [build evidence](../../compatibility/lang2c-hosted-build-evidence.json).
- The agent manifest is byte-identical to the recorded Phase 7 source manifest:
  same seven tools, six secret bindings, egress and managed-memory feature. No new
  secret upload, project policy, role, search index or memory setting is proposed.
- geo-intelligence-network remains on deploy-e5f6797e and is outside the mutation scope.

The staged bundle contains 49,304,903 regular-file bytes, below 52,428,800 bytes.
The pinned Linux/amd64 Docker build and all 96 hosted contracts passed. This is local
compatibility evidence, not a successful Engine build or live provider evaluation.

## Existing suspended work: explicit decision required

[Read-only inventory](../../compatibility/lang2c-rollout-inventory.json) found zero
pending/running/resuming executions and one suspended execution. Inspection identified:

- Execution: e1616bc3-b2a3-4974-bdf8-d4cc3c598da1.
- Created: 2026-10-29T17:54:47.35Z.
- Session: demo-invoice-a1416fe44ee243278e3d5fa40dade46f.
- Awaited tool: release_synthetic_recall.

Proposed resolution: cancel this exact old synthetic test through the native
execution-cancel endpoint, without approving its action. Require its status to become
cancelled. Cancellation ends that execution; do not promise that it can be resumed.
Preserve native history and memory. If the requester wants to preserve the suspended
test for later completion, defer deployment and investigate its compatible runtime.

The other three reserved runtimes belong to the completed LANG-2c document reviews.
Their exact execution/session pairs are in the inventory. Release only these verified
completed runtime reservations, preserving durable history. Do not stop unrelated
sessions or cancel newly discovered work. Recheck all active statuses immediately
before deployment and stop on any new pending/running/suspended/resuming execution.

Official contracts checked: [Agent Engine invocation and cancellation](https://www.mongodb.com/docs/agentengine/deploy/invoke-agent/)
and [execution-list API](https://www.mongodb.com/docs/api/doc/agentengine).
Runtime reservations alone are not proof that no suspended work exists.

## Remote build and activation

After authorization and preflight, upload only the hash-verified stage using an
explicit workspace/project/org target and no build-secret upload. Build one image,
record its exact build ID, and require success before deploying that build ID. Never
use implicit latest-build selection, automatic Atlas setup, --yes or --upload-build-secrets.
CLI build/deploy flags were checked against the installed CLI help.

Keep APP_JOURNEY_LOCALE_ENABLED=false on the existing demo process. Use an isolated
loopback backend for acceptance. The new source supports legacy settled English
results; this does not establish replay of old active workflows. Do not run v8 and
v9 against the same active execution. Existing demo servers are not restarted by
this proposal. Activation of locale admission follows the acceptance gates below.

## Bounded acceptance matrix

Maximum 20 new invocations, serial, in 30 minutes; no automatic invoke/provider retry.
Use the two existing private synthetic test accounts and retain native user identity
across language switches. Do not create an additional memory writer or account.

| Cases | New invocations | Required result |
| --- | --- | --- |
| Invoice in en-US/pt-BR/es-ES | 3 | Exact localized total/date, correct locale recovered from Engine's original message; one case uses a 4,000-character valid input to test carrier overhead |
| Governed knowledge in each locale | 3 | Exact reviewed source steps, language and document/version/page citation, without an LLM rewrite |
| Informational offer with explicit negation in each locale | 3 | Current price, no proposal or approval |
| Authorization injection in each locale | 3 | No access to another account and no unauthorized approval |
| Memory continuity: English preference seed, Portuguese and Spanish recall, other-user isolation | 4 | Same user's declared fiber-500 preference can inform comparison; no other-user disclosure or historical approval reuse |
| Synthetic change proposal in each locale | 3 | Same exact action/price after preference switch and recovery; reject one and approve two simulations, no real plan/charge change; deny stale digest, duplicate approval and another user |
| Legacy English admission without locale envelope | 1 | Legacy input still returns readable English result |

Recover every completed result without creating new invocations. For one new
suspended simulation, release only its test runtime reservation and recreate the
backend service, then verify the exact pending action before the requester decision.
This is same-version runtime recovery, not a platform outage or cross-version replay.
Allow bounded polling for native memory availability; do not issue extra test turns
if recall fails. Record semantic failures rather than changing reference expectations.

Each journey allows at most seven application-model calls with 1,024 output tokens
per call: at most 140 application-model calls for the 20 invocations. The three
knowledge cases additionally allow at most three query embeddings and three reranks.
Engine-managed memory may issue its own provider calls; do not present the application
cap as an all-provider count or a dollar-cost guarantee. Keep the existing USD 30
ceiling; this proposal does not reset the budget. Requester authorization of this new
evaluation envelope is required; the completed nine-call publication approval does
not cover it. No speech provider calls or load/capacity tests are included.

## Failure and rollback

Stop on unclear invoke outcome, failed build/deployment, unexpected shared-resource
change, cap exhaustion or failed protected output/authorization check. Record exact
owned sessions and statuses. Do not retry an uncertain request or silently cancel
someone else's work. Keep new locale admission off while diagnosing.

Rollback to the recorded v8 build is conditional on there being no active/suspended
v9 executions. Resolve only authorized test executions first, then deploy the exact
rollback build. Retain compatible application readers, source validators and all
published documents. Do not undo schema changes or delete memory to make rollback
appear successful. Confirm geo-intelligence-network's deployment is unchanged.

LANG-2c closes only after the remote gates and required PR checks pass. LANG-3 voice,
Control Plane, Tokenomics and mymemory migration remain separate plan phases.


## Execution record

[Drain evidence](../../compatibility/lang2c-rollout-drain-evidence.json) confirms the
exact legacy execution is cancelled, the three completed publication runtimes are
released, all four active-status counts are zero and the other workspace is unchanged.
Initial preflight encountered EngineUnavailable before mutation; private CLI refresh
succeeded and repeated preflight/drain passed. The source-tree hash matched approval.

Remote build bld_01M6CCNAB7QA912HBH54FB63ZP was started from the verified temporary
stage. CLI correctly warned that this stage has no Git checkout: source attribution
uses the recorded tree hash, not an invented commit SHA. The CLI was not upgraded.
The acceptance script's first dry run exposed an unnecessary adapter-package import
that required Engine SDK in the application environment. Loading only the standalone
locale templates removed that dependency; the dry run and script lint then passed.


Remote build succeeded and deployment deploy-f11e4d01 completed successfully.
The installed CLI advertised --workspace-id for deploy get but rejected it at
execution; using the exact deployment ID plus explicit project/org succeeded.
A build-log read hit sandbox DNS restrictions; the authorized escalation succeeded.

The first evaluation preflight stopped with AssertionError and zero invocations:
workspace.current_deployment_id and `agentengine status` still reported deploy-af009ed4.
The documented `workspaces/{id}/deployments/current` endpoint reported deploy-f11e4d01,
the expected build, succeeded status, RolloutComplete=True and all components ready.
The evaluator now verifies this authoritative active-deployment endpoint. The earlier
failure is preserved in compatibility/lang2c-hosted-preflight-failure.json; no model
call was retried. Do not weaken the gate to accept a healthy but wrong build.


Final outcome: all 20 hosted cases passed in 486.41 seconds; both profiles restored.
The isolated HTTP backend recovered all 20 identical results and rejected all 20
cross-user reads, adding no provider calls. Existing demo servers were not restarted.
See [hosted evidence](../../compatibility/lang2c-hosted-acceptance.json) and
[HTTP evidence](../../compatibility/lang2c-http-recovery-evidence.json). The private
local locale flag is enabled for the next backend start; other deployments retain
the safe default until validated. Voice localization remains a separate gate.
