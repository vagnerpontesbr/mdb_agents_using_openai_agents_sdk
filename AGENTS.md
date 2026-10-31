# Working on the Telecom Agent Asset

## Start here

- Phase 0 bounded compatibility is complete; read the current [checkpoint](docs/compatibility/PHASE_0.md) and [publication/CI status](docs/runbooks/REPOSITORY_SETUP.md). Phase 1 application foundation is tracked in [FND-003](docs/tasks/FND-003-FOUNDATION.md); use the [application runbook](docs/runbooks/APPLICATION.md). Phase 2 bounded acceptance is complete: [VERT-001/002](docs/tasks/VERT-001-JOURNEY.md) and the [Phase 2 runbook](docs/runbooks/PHASE_2.md) record local checks, hosted/native review and user-confirmed voice acceptance. Phase 2 publication/CI passed. Phase 3 bounded memory/recovery acceptance passed in [MEM-001](docs/tasks/MEM-001-MEMORY.md); use the [Phase 3 runbook](docs/runbooks/PHASE_3.md). Phase 3 and its CI correction are published with passing CI. The user authorized Phase 4; [RAG-001](docs/tasks/RAG-001-KNOWLEDGE.md) records completed bounded curation/publication and hosted knowledge acceptance; publication and CI are verified at `1a52afc`. The user authorized continuing with Phase 5; [EVAL-001](docs/tasks/EVAL-001-QUALITY.md) records completed bounded Phase 5 acceptance, calibrated candidate cache and final hosted verification; Phase 5 commit `1a81be6` is published with passing CI. Phase 6 experience/packaging is complete with MIT and requester-accepted automated clean-checkout handoff; [REL-001](docs/tasks/REL-001-HANDOFF.md) records evidence. Phase 6 is published as `9b048bb`, with correction `a4f5c4c` and passing CI `41207242615`. Phase 7 runtime acceptance is complete for the bounded demo; its documentation/evidence awaits manual publication. Phase 8 scalability/resilience has not started.
- Read [initial_plan.md](initial_plan.md) for scope, [requirements](docs/REQUIREMENTS.md) for user decisions, and the relevant [ADR](docs/adr/README.md) before changing architecture.
- Use [the task backlog](docs/tasks/README.md) to choose a bounded deliverable and record evidence. The latest explicit user instruction takes precedence over repository guidance.
- All code, documentation, UI, prompts, and example conversations are English.

## Architecture invariants

- Prefer Agent Engine for overlapping platform capabilities, following [ADR-0018](docs/adr/0018-engine-feature-precedence.md). Do not create parallel SDK memory, approval, replay, policy or primary trace owners; report unsupported integration as blocked.
- OpenAI Agents SDK remains the orchestrator. Validate Engine memory and hosted execution separately; never describe untested adapters as supported.
- Use the approved two-cluster boundary in [ADR-0017](docs/adr/0017-two-cluster-memory-boundary.md): OpenAI-SDK for application data and ClusterDemoTelco for project-managed Engine memory. Preserve service/domain ownership and least-privilege identities. Test tenant/ACL filters separately from database roles.
- Prefer MongoDB Auto Embedding where the requested model/workflow is supported. Preserve voyage-context-4 for contextual knowledge and native MongoDB hybrid fusion.
- Agent Engine owns its managed memory. Do not add a competing memory writer. Demo scope is semantic/episodic continuity ([ADR-0021](docs/adr/0021-demo-semantic-episodic-continuity.md)), private backend CLI identity ([ADR-0022](docs/adr/0022-demo-private-engine-cli-identity.md)), and quiet-environment voice ([ADR-0023](docs/adr/0023-quiet-environment-demo-voice.md)).
- Keep ingestion/OCR outside interactive execution. Keep specialists in the shared runtime unless an ADR justifies extraction.
- Enforce permissions, document validity, business rules, idempotency, and critical-response templates in backend code. A model prompt or similarity score cannot authorize an action.
- Formal intent catalogs, ontologies, and a dedicated intent classifier are out of scope.

## Development workflow

- Inspect existing files and Git status when available; preserve unrelated work. Never overwrite remote history or invent a successful Git operation.
- The user performs Git commits, pushes, and PR creation manually. Prepare and validate changes, then provide commands; verify results through read access. Do not attempt GitHub plugin writes.
- Implement one plan phase at a time. At a completed phase boundary, stop and provide the manual commit commands; wait for the user's confirmation before starting the next phase. A blocked compatibility gate is not a completed phase.
- Deliver a small end-to-end behavior or compatibility proof with explicit acceptance criteria. Avoid broad scaffolding that hides unvalidated dependencies.
- Use uv for Python dependencies and interpreter management; commit the validated lock and frontend lock when those projects exist. Do not silently downgrade the requested Python target.
- Verify external SDK APIs against official documentation and the pinned version. Record tested versions, environment, and unresolved gaps.
- Keep one authoritative specification per concern; link to it rather than duplicating policy across files. Add/supersede ADRs for material decisions.
- No secrets, personal data, raw recordings, or customer documents in fixtures/logs/commits. Use synthetic data. Credentials belong in injected configuration.
- Do not create extra agents, skills, services, or configuration without a task-driven need. Follow explicit delegation instructions when provided.

## Commands that work now

From the project root, run `python3 scripts/check_repository.py` after documentation or repository-workflow changes. It is a standard-library bootstrap check, not application validation. Optional uv invocation is documented in [CONTRIBUTING.md](CONTRIBUTING.md).

Phase 0 diagnostics: `python3 -m unittest discover -s tests/compatibility -v` tests the probe harness. `python3 scripts/check_compatibility.py` reports metadata/import/prerequisite evidence; nonzero status can report unconfigured local prerequisites or unrequested live checks; it does not replace the recorded Phase 0 acceptance. See [the Phase 0 runbook](docs/compatibility/PHASE_0.md) before any explicit live probe.

Root application commands: `uv sync --frozen`, `uv run --frozen ruff check src/telecom_app tests/foundation`, `uv run --frozen mypy`, `uv run --frozen pytest -q`, and `uv build --no-build-isolation`. Frontend: `npm --prefix apps/web ci`, `npm --prefix apps/web run lint`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web test`, `npm --prefix apps/web run build`, and `npm --prefix apps/web run test:e2e` (Chromium installed). Identity and hosted-contract commands remain in CONTRIBUTING.md. Run checks relevant to the changed boundary. Separate deterministic CI from credentialed provider evaluations and bounded stress runs.

## Code Review Rules

- Flag tenant/ACL bypass, cross-service writes, broad credentials, stale-source/cache use, missing idempotency, or approvals detached from exact actions.
- Flag schema-valid output being treated as factually correct or claims of guaranteed LLM determinism.
- Flag mock results presented as provider compatibility, capacity, or measured RAG quality.
- Flag duplicate memory persistence, uncontrolled retries/fan-out, unbounded queues/history, or undocumented external costs.
- Require meaningful validation and the relevant document/ADR update. Use exact text assertions for templates, not arbitrary LLM prose.

## Completion report

State changed behavior, files/decisions, checks actually run and their results, and remaining limitations. Distinguish locally authored files from committed, pushed, deployed, or remotely verified work.

Current runtime acceptance: [RUN-001](docs/tasks/RUN-001-RUNTIME.md). Stop at the completed Phase 7 boundary for manual commit/push before Phase 8.
