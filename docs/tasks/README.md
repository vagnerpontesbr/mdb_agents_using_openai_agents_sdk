# Implementation backlog

The [initial plan](../../initial_plan.md) defines scope; this backlog sequences reviewable deliveries. Owners are assigned when work starts. Every task uses the [template](TEMPLATE.md) and records actual evidence. “Ready” means scoped, not tested.

| ID | Deliverable | Dependency | Acceptance | Status |
|---|---|---|---|---|
| FND-001 | Codex instructions, docs validation, PR templates, development ADRs | None | Local checker passes; status honestly distinguishes authored files from GitHub setup | Done locally |
| FND-002 | Reconcile local files with intended GitHub repository | User Terminal for Git writes | Remote history preserved; branch and PR verified; CI results recorded | `43746c6` published; integration tracked in PR #1; disconnect-test fix `60ef97b` published; push and PR CI passed; [publication status](../runbooks/REPOSITORY_SETUP.md) |
| COMP-001 | Latest-Python dependency proof | Provider/package access | uv lock/sync/import/build on target; record compatible versions and failures; no silent downgrade | Passed for bounded split Python environments and bundled Python 3.15.2 hosted build; [dependency evidence](COMP-001-DEPENDENCIES.md). Future application dependencies remain separate. |
| COMP-002 | Engine memory and designated-cluster proof | Atlas/Engine access, COMP-001 | Real record/context/isolation check on intended cluster; document supported schema/credentials without secrets | Passed for designated Engine memory cluster, managed projection, durable recall and bounded isolation controls; [memory evidence](COMP-002-DIAGNOSTICS.md). Native expurgo accepted by user. |
| COMP-003 | Engine hosted execution proof | COMP-001, platform access | Verify SDK orchestration, tool/LLM audit, replay, approval/resume; report unsupported contract explicitly | Passed for bounded hosted orchestration, native review/replay/recovery, semantic/episodic recall, concurrency and injected dependency failure; [hosted evidence](COMP-003-HOSTED.md), [fault/restoration evidence](COMP-003-FAULTS.md). Chronological restoration excluded by ADR-0021; full framework implementation remains future work. |
| COMP-004 | Voyage/search/voice capability probes | COMP-001, provider access | Actual auto-chunk, dimensions, fusion, Auto Embedding and voice/session contract results | Passed for scoped [search](COMP-004-SEARCH.md) and [voice](COMP-004-VOICE.md) compatibility, including real microphone/listening. Quiet-environment voice accepted in ADR-0023; noise robustness and application RAG quality remain outside this checkpoint. |
| COMP-005 | Requester authorization and thirty-day memory lifecycle | COMP-002, COMP-003 | Authenticated self-approval and denied other-user controls; native expurgo accepted without additional proof | Passed for [demo identity, requester-only admission and restricted application database permissions](COMP-005-DEMO-AUTH.md). Private Engine CLI identity accepted in ADR-0022; native expurgo proof waived by user. |
| FND-003 | Backend/frontend manifests and CI | COMP-001 | Frozen installs, imports/builds, lint/types and relevant tests; no fake lockfiles | Ready |
| VERT-001 | First authenticated financial request | FND-003 | Typed intent, validated tool, simulated invoice, approved template, denied access and idempotency cases | Ready |
| VERT-002 | Three specialists plus browser voice | VERT-001, COMP-004 | Mixed-intent route, mic/transcript/playback, shared context, cancellation and failure cases | Ready |
| MEM-001 | Memory and interrupted-run persistence | COMP-002, VERT-001 | Continuity, isolated tenants, concurrency and resume evidence; native expurgo accepted by user | Ready |
| RAG-001 | Governed PDF ingestion and retrieval | COMP-004, FND-003 | Text/scanned PDFs, version publication, owner/risk enforcement, native search/rerank citations | Ready |
| EVAL-001 | Stale-document/cache/determinism experiments | RAG-001, MEM-001 | Independent current truth; actual metrics; invalidation and repeated-run reports | Ready |
| OPS-001 | Load and resilience profiles | VERT-002, RAG-001, EVAL-001 | Separate mocks/live-provider results; budgets, resource contention and invariants across the approved cluster boundaries | Ready |
| REL-001 | Reproducible client handoff | Prior accepted tasks | Fresh setup/demo/adaptation trial, license/notice decision, deployment caveats and runbooks | Ready |

**Phase 0 checkpoint:** COMP-001 through COMP-005 are accepted for the bounded
demo scope documented in [Phase 0](../compatibility/PHASE_0.md), with explicit
ADR-0021/0022/0023 limitations and user-accepted native expurgo. Final restoration
and positive recall passed. The detailed task histories preserve broader limits;
those are not claims of full application or production acceptance. Implementation/evidence was committed and pushed as `43746c6`. The documentation reconciliation follows that checkpoint; remote push and PR CI passed for fix `60ef97b`. Do not start FND-003/Phase 1 yet.

Implementation tasks can be subdivided before coding. Failed compatibility gates should drive explicit decisions, not speculative implementations. Remote review and publishing remain distinct from local completion.

User-defined phase gate: stop after each completed phase, provide manual commit commands, and wait for confirmation before the next phase. [Phase 0 evidence and runbook](../compatibility/PHASE_0.md) records the completed bounded checkpoint; commit/push completed; await user confirmation before the next phase.

VERT-001 includes an explicit `@function_tool` invoice walkthrough; VERT-002 includes approved simulated plan changes; RAG-001 includes curator-only ingestion jobs. EVAL-001 implements calibrated offline LLM-as-judge grading with independent time-valid references. Online judge gating is optional and disabled by default; deterministic policy checks remain mandatory.

FND-001 evidence: `python3 scripts/check_repository.py` and the offline uv invocation passed locally on Python 3.14.6/uv 0.11.3. Temporary negative fixtures verified detection of broken/nonportable links, missing ADR context, and missing AGENTS.md. A path-normalization defect discovered by those fixtures was corrected and the cases passed. GitHub CI subsequently passed for published foundation commit `3c29d14`; later local edits require a new run. See the [setup runbook](../runbooks/REPOSITORY_SETUP.md).
