# Working on the Telecom Agent Asset

## Start here

- Additional planned tracks: [MEM-002](docs/tasks/MEM-002-MYMEMORY-MIGRATION.md) for Engine memory on mymemory and [TOK-001](docs/tasks/TOK-001-TOKENOMICS.md) for Control Plane dashboards. Verify shared-project impact and supported migration before a live switch. Do not expose private URIs or invent missing usage/prices.


- Current requested work: [UI-001](docs/tasks/UI-001-PROFILES-CONTROL-PLANE.md). UI-0, UI-1 and UI-2a merged (PRs #5, #6 and #7; latest base `c62b99a`). UI-2b profile photo is implemented on `codex/ui-2b-avatar`, local gates passed and publication pending. The approved identity UPDATE permission remains scoped to telecom_identity.users. Password, remaining multilingual gates, settings, actual-cost dashboards and mymemory migration remain subsequent phases.


- Phases 0–8 are complete for the approved demo scope and integrated through PR #4 (`e524a57`). Use [the task backlog](docs/tasks/README.md) and linked runbooks for historical evidence and limitations. Use UI-001 for current UI progress; multilingual, Tokenomics data and mymemory migration remain planned.
- Read [initial_plan.md](initial_plan.md) for scope, [requirements](docs/REQUIREMENTS.md) for user decisions, and the relevant [ADR](docs/adr/README.md) before changing architecture.
- Use [the task backlog](docs/tasks/README.md) to choose a bounded deliverable and record evidence. The latest explicit user instruction takes precedence over repository guidance.
- Source identifiers and developer documentation remain English. The requester now requires pt-BR, en-US and es-ES for UI, agent responses and voice; localized catalogs/templates/fixtures are expected. Follow [I18N-001](docs/tasks/I18N-001-MULTILINGUAL.md).

## Architecture invariants

- Prefer Agent Engine for overlapping platform capabilities, following [ADR-0018](docs/adr/0018-engine-feature-precedence.md). Do not create parallel SDK memory, approval, replay, policy or primary trace owners; report unsupported integration as blocked.
- OpenAI Agents SDK remains the orchestrator. Validate Engine memory and hosted execution separately; never describe untested adapters as supported.
- Use the approved two-cluster boundary in [ADR-0017](docs/adr/0017-two-cluster-memory-boundary.md): OpenAI-SDK for application data and ClusterDemoTelco for project-managed Engine memory. Preserve service/domain ownership and least-privilege identities. Test tenant/ACL filters separately from database roles.
- Prefer MongoDB Auto Embedding where the requested model/workflow is supported. Preserve voyage-context-4 for contextual knowledge and native MongoDB hybrid fusion.
- Agent Engine owns its managed memory. Do not add a competing memory writer. Demo scope is semantic/episodic continuity ([ADR-0021](docs/adr/0021-demo-semantic-episodic-continuity.md)), private backend CLI identity ([ADR-0022](docs/adr/0022-demo-private-engine-cli-identity.md)), and quiet-environment voice ([ADR-0023](docs/adr/0023-quiet-environment-demo-voice.md)).
- Keep ingestion/OCR outside interactive execution. Keep specialists in the shared runtime unless an ADR justifies extraction.
- Enforce permissions, document validity, business rules, idempotency, and critical-response templates in backend code. A model prompt or similarity score cannot authorize an action.
- Language changes must preserve the active conversation and execution identity; follow [I18N-001](docs/tasks/I18N-001-MULTILINGUAL.md) for in-flight text/audio and continuity tests.
- Tokenomics cost dashboards must use real source-reported monetary values. Estimates, fixtures and missing prices cannot stand in for actual costs; follow [TOK-001](docs/tasks/TOK-001-TOKENOMICS.md) for provenance and acceptance.
- Control Plane editing is limited to application limits and retrieval-cache settings. Feature toggles remain read-only. Save/Apply affects subsequent operations only; preserve in-flight configuration snapshots and do not add restart/deploy controls. UI-001 owns the acceptance tests.
- Formal intent catalogs, ontologies, and a dedicated intent classifier are out of scope.

## Development workflow

- Keep this file current whenever a task changes durable instructions, supported commands, architecture boundaries or delivery workflow. Reconcile obsolete instructions in the same change; link to authoritative plans instead of accumulating status history.
- Local changes within the requested scope may proceed without asking for permission; preserve unrelated work and existing safety constraints. Before any Atlas mutation that could affect other projects or shared consumers, stop and ask the requester with the exact proposed change, affected scope and rollback implications. Read-only inventory may proceed; uncertain shared impact must be resolved before mutation.
- Inspect existing files and Git status when available; preserve unrelated work. Never overwrite remote history or invent a successful Git operation.
- The requester authorizes the agent to commit scoped, reviewed changes, push the phase branch and create or update its PR without asking for confirmation. This supersedes previous manual-publication instructions. Required sandbox/tool approvals still apply; do not bypass branch protections or overwrite remote history.
- Implement one plan phase/subphase at a time. At its boundary, record evidence, publish the dedicated PR and verify required CI. Follow the previously authorized quality-gated automatic merge workflow, then start the next branch from integrated main. Do not pause solely to request commit/PR permission; stop for unresolved material decisions or potentially shared Atlas changes. A blocked compatibility gate is not a completed phase.
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

State changed behavior, files/decisions, checks actually run and their results, and remaining limitations. For each local or CI validation, list the executed commands/suites, their covered behavior and results (including skipped or unexecuted checks). For remote CI, identify the commit and run link/ID. Explain every failed test/check with its name, expected versus actual behavior, known cause or unresolved diagnosis, correction and rerun result. Distinguish infrastructure failures from behavioral regressions; a later green run does not erase the failure report. Never describe planned checks as executed. Distinguish locally authored files from committed, pushed, deployed, or remotely verified work.

Current runtime acceptance: [RUN-001](docs/tasks/RUN-001-RUNTIME.md). The user authorized Phase 8 and a USD 30 total provider budget, retaining current direct OpenAI/gateway paths; [OPS-001](docs/tasks/OPS-001-RESILIENCE.md) owns these decisions. The requester accepted completion without production-capacity or pricing proof. Preserve measured limitations; current-cycle publication follows the workflow above.
