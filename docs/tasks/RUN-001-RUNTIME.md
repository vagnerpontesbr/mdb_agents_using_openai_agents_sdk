# RUN-001: Engine runtime target

- Status: Complete for the bounded demo; Phase 7 documentation/evidence awaiting manual publication
- Owner: Telecom demo maintainer
- Dependencies: COMP-003, VERT-001/002, MEM-001, RAG-001, EVAL-001, REL-001
- Decisions: [ADR-0018](../adr/0018-engine-feature-precedence.md), [ADR-0021](../adr/0021-demo-semantic-episodic-continuity.md), [ADR-0022](../adr/0022-demo-private-engine-cli-identity.md), [ADR-0025](../adr/0025-phase-two-journey.md)

## Acceptance and contract

Validate the packaged entrypoint, SDK orchestration, external tools, Engine memory,
primary traces/replay and runtime recovery. Preserve the accepted synthetic scope;
do not introduce a native vendor-support claim or a second platform owner.
[The adapter contract](../../compatibility/openai_engine_adapter/README.md) owns
implementation bounds; [the runbook](../runbooks/PHASE_7.md) owns reproduction.

## Evidence matrix — 2026-10-31

| Requirement | Evidence | Scope |
| --- | --- | --- |
| Hosted entrypoint | `knowledge_review:app`, workflow 8, deployment `deploy-af009ed4` | Existing deployed build; no redeployment in this phase |
| SDK and external calls | [Final Phase 5 journey](../../compatibility/phase5-journey-final-evidence.json) | Eight real hosted invoice/sales/mixed/knowledge runs passed; reused evidence |
| Runtime availability | [Phase 7 runtime evidence](../../compatibility/phase7-runtime-evidence.json) | Fresh health read: OE 2, memory 1, agent 4, tool 4 ready |
| Local integration contract | 86 hosted-contract tests passed on macOS in frozen environment | Remote boundaries doubled; not provider acceptance |
| Managed memory | [MEM-001](MEM-001-MEMORY.md) plus Phase 7 core hashes | Historical live semantic/episodic continuity and user isolation; unchanged memory modules |
| Native review and recovery | [Phase 7 recovery evidence](../../compatibility/phase7-recovery-evidence.json) | Fresh workflow 8 proof with two actual authenticated synthetic accounts |
| Replay and audit | [MEM-001](MEM-001-MEMORY.md), [Phase 5 trace metrics](../../compatibility/phase5-final-trace-metrics.json) | Historical replay without extra model calls; current workflow session-level primary traces |

The fresh recovery proof created one synthetic fiber-1000 proposal, checked its
owner/session/state, stopped only its runtime, and confirmed that runtime absent.
A recreated application service recovered the exact pending action. Another user
and a stale digest were denied; the requester approved the action and received the
exact USD 109.90 simulation receipt. Duplicate approval was denied and completed
state remained recoverable. The completed test runtime received a stop request;
durable Engine records were preserved. No real subscription or charge changed.

A fresh knowledge-review source stage matches all 31 Python-file hashes in the
deployed Phase 5 manifest and includes the exact root MIT license and correct
entrypoint. This source-only check does not rebuild the Linux interpreter.

Nine core modules match both Phase 3 and deployed Phase 5 source hashes, including
memory, native review, deadlines, provider and domain code. Journey orchestration
changed since Phase 3; the fresh workflow 8 recovery proof covers its current path.
Hash equality alone is not a claim of universal replay or cross-version migration.

## Limitations and completion

No platform VM failure was injected. Phase 7 did not remeasure native trace call
counts; duplicate approval denial is not a new exactly-once platform guarantee.
Phase 5 traces correlate by session because root execution IDs were null; redacted
arguments prevent parameter-accuracy metrics. Chronological history is excluded,
native 30-day expurgo is accepted without a new test, and the private CLI backend
identity remains a demo exception. Capacity, scale-out and overload acceptance
belong to Phase 8 and remain unimplemented/unmeasured.

Phase 6 commit `9b048bb` and correction `a4f5c4c` are published; correction CI
[41207242615](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41207242615)
passed. Phase 7 adds contract/documentation reconciliation and bounded evidence,
not a runtime code change. Stop for manual commit/push before Phase 8.

Final documentation checks passed: 80 Markdown files, 28 ADRs and `git diff --check`.
The initial ADR validation identified missing standard sections; these were added
and the checker then passed. No application code changed in this phase.
