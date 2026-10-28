# Implementation backlog

The [initial plan](../../initial_plan.md) defines scope; this backlog sequences reviewable deliveries. Owners are assigned when work starts. Every task uses the [template](TEMPLATE.md) and records actual evidence. “Ready” means scoped, not tested.

| ID | Deliverable | Dependency | Acceptance | Status |
|---|---|---|---|---|
| FND-001 | Codex instructions, docs validation, PR templates, development ADRs | None | Local checker passes; status honestly distinguishes authored files from GitHub setup | Done locally |
| FND-002 | Reconcile local files with intended GitHub repository | User Terminal for Git writes | Remote history preserved; foundation commit/branch and successful CI verified; PR remains pending | Branch published; PR pending |
| COMP-001 | Latest-Python dependency proof | Provider/package access | uv lock/sync/import/build on target; record compatible versions and failures; no silent downgrade | [Local split dependency proof](COMP-001-DEPENDENCIES.md) passed: locks, frozen installs, imports/builds and CPU PDF/OCR on macOS ARM64; hosted/Linux compatibility remains separate |
| COMP-002 | Engine memory and designated-cluster proof | Atlas/Engine access, COMP-001 | Real record/context/isolation check on intended cluster; document supported schema/credentials without secrets | [Atlas inspection and diagnostic evidence](COMP-002-DIAGNOSTICS.md): authenticated CLI confirms target scope for the user-confirmed Engine identity; generation 10 and memory-server v0.11.11 applied; synthetic STM write/read and distinct-user/session control pass; text/semantic/hybrid retrieval pass; tenant authorization and durable extraction remain open; two-cluster topology approved in ADR-0017 |
| COMP-003 | Engine hosted execution proof | COMP-001, platform access | Verify SDK orchestration, tool/LLM audit, replay, approval/resume; report unsupported contract explicitly | Ready |
| COMP-004 | Voyage/search/voice capability probes | COMP-001, provider access | Actual auto-chunk, dimensions, fusion, Auto Embedding and voice/session contract results | OpenAI/Voyage HTTP passed; [bounded search proof](COMP-004-SEARCH.md) passed with Auto Embedding/native fusion and prefilters; [synthetic voice/chat proof](COMP-004-VOICE.md) passed; browser/Engine continuity and remaining model/index paths pending |
| FND-003 | Backend/frontend manifests and CI | COMP-001 | Frozen installs, imports/builds, lint/types and relevant tests; no fake lockfiles | Ready |
| VERT-001 | First authenticated financial request | FND-003 | Typed intent, validated tool, simulated invoice, approved template, denied access and idempotency cases | Ready |
| VERT-002 | Three specialists plus browser voice | VERT-001, COMP-004 | Mixed-intent route, mic/transcript/playback, shared context, cancellation and failure cases | Ready |
| MEM-001 | Memory and interrupted-run persistence | COMP-002, VERT-001 | Continuity, isolated tenants, concurrency, deletion and resume evidence | Ready |
| RAG-001 | Governed PDF ingestion and retrieval | COMP-004, FND-003 | Text/scanned PDFs, version publication, owner/risk enforcement, native search/rerank citations | Ready |
| EVAL-001 | Stale-document/cache/determinism experiments | RAG-001, MEM-001 | Independent current truth; actual metrics; invalidation and repeated-run reports | Ready |
| OPS-001 | Load and resilience profiles | VERT-002, RAG-001, EVAL-001 | Separate mocks/live-provider results; budgets, resource contention and invariants across the approved cluster boundaries | Ready |
| REL-001 | Reproducible client handoff | Prior accepted tasks | Fresh setup/demo/adaptation trial, license/notice decision, deployment caveats and runbooks | Ready |

Implementation tasks can be subdivided before coding. Failed compatibility gates should drive explicit decisions, not speculative implementations. Remote review and publishing remain distinct from local completion.

User-defined phase gate: stop after each completed phase, provide manual commit commands, and wait for confirmation before the next phase. [Phase 0 evidence and runbook](../compatibility/PHASE_0.md) currently records blockers; this is not yet a completed-phase commit checkpoint.

VERT-001 includes an explicit `@function_tool` invoice walkthrough; VERT-002 includes approved simulated plan changes; RAG-001 includes curator-only ingestion jobs. EVAL-001 implements calibrated offline LLM-as-judge grading with independent time-valid references. Online judge gating is optional and disabled by default; deterministic policy checks remain mandatory.

FND-001 evidence: `python3 scripts/check_repository.py` and the offline uv invocation passed locally on Python 3.14.6/uv 0.11.3. Temporary negative fixtures verified detection of broken/nonportable links, missing ADR context, and missing AGENTS.md. A path-normalization defect discovered by those fixtures was corrected and the cases passed. GitHub CI subsequently passed for published foundation commit `3c29d14`; later local edits require a new run. See the [setup runbook](../runbooks/REPOSITORY_SETUP.md).
