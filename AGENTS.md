# Working on the Telecom Agent Asset

## Start here

- This workspace currently contains planning, synthetic fixtures, and repository checks. Application/provider integrations are not implemented.
- Read [initial_plan.md](initial_plan.md) for scope, [requirements](docs/REQUIREMENTS.md) for user decisions, and the relevant [ADR](docs/adr/README.md) before changing architecture.
- Use [the task backlog](docs/tasks/README.md) to choose a bounded deliverable and record evidence. The latest explicit user instruction takes precedence over repository guidance.
- All code, documentation, UI, prompts, and example conversations are English.

## Architecture invariants

- OpenAI Agents SDK remains the orchestrator. Validate Engine memory and hosted execution separately; never describe untested adapters as supported.
- Use the approved two-cluster boundary in [ADR-0017](docs/adr/0017-two-cluster-memory-boundary.md): OpenAI-SDK for application data and ClusterDemoTelco for project-managed Engine memory. Preserve service/domain ownership and least-privilege identities. Test tenant/ACL filters separately from database roles.
- Prefer MongoDB Auto Embedding where the requested model/workflow is supported. Preserve voyage-context-4 for contextual knowledge and native MongoDB hybrid fusion.
- Agent Engine owns its managed memory. Do not add a competing memory writer.
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

Phase 0 diagnostics: `python3 -m unittest discover -s tests/compatibility -v` tests the probe harness. `python3 scripts/check_compatibility.py` reports metadata/import/prerequisite evidence; nonzero status is expected while compatibility is blocked. See [the Phase 0 runbook](docs/compatibility/PHASE_0.md) before any explicit live probe.

There are no application build/lint/type commands yet. Add actual commands with the implementation; do not report placeholders as passing checks. Future changes must run the relevant behavior/contract tests, lint/types, and builds. Separate deterministic CI from credentialed provider evaluations and bounded stress runs.

## Code Review Rules

- Flag tenant/ACL bypass, cross-service writes, broad credentials, stale-source/cache use, missing idempotency, or approvals detached from exact actions.
- Flag schema-valid output being treated as factually correct or claims of guaranteed LLM determinism.
- Flag mock results presented as provider compatibility, capacity, or measured RAG quality.
- Flag duplicate memory persistence, uncontrolled retries/fan-out, unbounded queues/history, or undocumented external costs.
- Require meaningful validation and the relevant document/ADR update. Use exact text assertions for templates, not arbitrary LLM prose.

## Completion report

State changed behavior, files/decisions, checks actually run and their results, and remaining limitations. Distinguish locally authored files from committed, pushed, deployed, or remotely verified work.
