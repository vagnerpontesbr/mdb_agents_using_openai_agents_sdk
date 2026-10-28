# Contributing

The intended repository is [vagnerpontesbr/mdb_agents_using_openai_agents_sdk](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk). Read [AGENTS.md](AGENTS.md) and the relevant task/ADR before working. Repository foundation is present; application implementation remains pending.

## Local validation

The bootstrap checker uses only the Python standard library:

```bash
python3 scripts/check_repository.py
```

With uv and an existing system interpreter, the equivalent offline command is:

```bash
uv run --no-project --no-managed-python --offline python3 scripts/check_repository.py
```

This does not resolve or validate the application dependency graph. Phase 0 must establish the target interpreter and actual SDK compatibility; use uv and a committed lock for the future application. Current foundation was checked with system Python 3.14.6, not a claim that the planned application target has passed.

The [local dependency proof](docs/tasks/COMP-001-DEPENDENCIES.md) now provides two frozen compatibility environments and actual build commands for macOS ARM64. These diagnostic packages do not replace the future application/frontend manifests.

## Task and review workflow

1. Inspect current state and select one task from the [backlog](docs/tasks/README.md).
2. Record scope, dependencies, acceptance, and evidence using the [task template](docs/tasks/TEMPLATE.md).
3. Work on a focused branch once Git access exists. Review the existing remote history before integrating local files; do not force-push or replace remote content.
4. Make a small reviewable change. Update contracts and the authoritative documentation together.
5. Run relevant checks. Document unavailable checks and why; mocks cannot certify live integrations.
6. Review the diff for accidental secrets, generated data, unrelated edits, and unmet scope. Describe behavior, validation, and limitations in the PR.
7. Mark a task complete only when its stated acceptance evidence exists. Review/merge and deployment are distinct events.

The PR template and workflow are local files until uploaded. Branch protection, required checks, and GitHub Codex review integration require repository-side configuration; none is automatically enabled by adding AGENTS.md.

## Validation levels

Phase 0 now adds `python3 -m unittest discover -s tests/compatibility -v` and `python3 scripts/check_compatibility.py`. The former tests the diagnostic harness; the latter returns nonzero when prerequisites fail or remain blocked. See [Phase 0](docs/compatibility/PHASE_0.md) before running any live probe. Diagnostic success is not application compatibility.

The user executes commits, pushes, and PR creation manually. Stop at each completed implementation phase and wait for the user's commit confirmation before beginning the next one. Do not label an unresolved phase complete merely to reach a commit checkpoint.

| Level | Purpose | Status |
|---|---|---|
| Repository check | Local Markdown links, key foundation files, ADR sections/IDs | Available |
| Unit/contract | Deterministic policies and adapter behavior | Add with implementation |
| Build/lint/types | Reproducible backend/frontend checks | Add with manifests |
| Provider integration | Actual version/account/API compatibility | Phase 0 and feature tasks |
| Evals/load | Quality, cost, stability, and capacity | Separate explicit workloads and budgets |

Do not install custom skills or modify a developer's global Codex configuration merely to contribute. Root instructions link to detailed specifications; add nested guidance only when a real subsystem needs it.

## Licensing

A project license has not yet been selected. Record the owner's license decision and third-party notices before distributing this asset as a reusable licensed release. Do not infer a license from dependencies or the repository URL.
