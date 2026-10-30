# Contributing

The intended repository is [vagnerpontesbr/mdb_agents_using_openai_agents_sdk](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk). Read [AGENTS.md](AGENTS.md) and the relevant task/ADR before working. Phase 0 bounded compatibility is complete; Phase 1 foundation is implemented locally; see [FND-003](docs/tasks/FND-003-FOUNDATION.md). The full application journey has not started. See the [current checkpoint](docs/compatibility/PHASE_0.md) and [publication/CI status](docs/runbooks/REPOSITORY_SETUP.md).

## Application validation

Use the exact Python 3.15.2 interpreter and frozen root lock. The [application runbook](docs/runbooks/APPLICATION.md) lists backend lint/types/tests/build and frontend lint/types/unit/build/browser commands. Root checks cover the new typed application boundary; existing identity code retains its Phase 0 suite.

## Repository validation

The bootstrap checker uses only the Python standard library:

```bash
python3 scripts/check_repository.py
```

With uv and an existing system interpreter, the equivalent offline command is:

```bash
uv run --no-project --no-managed-python --offline python3 scripts/check_repository.py
```

This checks documentation structure only. Phase 0 separately validated the pinned Python environments and bounded SDK/provider integration. The root application and frontend now have their own validated lockfiles.

The [local dependency proof](docs/tasks/COMP-001-DEPENDENCIES.md) now provides frozen split compatibility environments and actual build commands for macOS ARM64. These diagnostic packages do not replace the future application/frontend manifests.

## Task and review workflow

1. Inspect current state and select one task from the [backlog](docs/tasks/README.md).
2. Record scope, dependencies, acceptance, and evidence using the [task template](docs/tasks/TEMPLATE.md).
3. Work on a focused branch. Review the existing remote history before integrating local files; do not force-push or replace remote content.
4. Make a small reviewable change. Update contracts and the authoritative documentation together.
5. Run relevant checks. Document unavailable checks and why; mocks cannot certify live integrations.
6. Review the diff for accidental secrets, generated data, unrelated edits, and unmet scope. Describe behavior, validation, and limitations in the PR.
7. Mark a task complete only when its stated acceptance evidence exists. Review/merge and deployment are distinct events.

The PR template and repository workflow are published. Branch protection, required checks, and GitHub Codex review integration require repository-side configuration; none is automatically enabled by adding AGENTS.md.

## Validation levels

Run the deterministic suites from the repository root:

```sh
python3 -m unittest discover -s tests/compatibility -v
python3 -m unittest discover -s tests/demo_auth -v
uv run --project compatibility/hosted-runtime --frozen --no-sync python -m unittest discover -s tests/hosted_contract -v
```

The hosted suite requires its installed pinned environment. Compatibility and
hosted tests include loopback sockets; a sandbox may require local-network
permission. These are not credentialed provider requests. Counts and evidence
are maintained in [Phase 0](docs/compatibility/PHASE_0.md).

`python3 scripts/check_compatibility.py` remains an opt-in diagnostic harness:
nonzero may mean missing local prerequisites or an unrequested live check, not
that the completed Phase 0 evidence has been invalidated. Consult the runbook
before live probes. The workflow retains repository, compatibility and demo identity suites and adds
a Phase 1 application job. That job installs frozen dependencies, runs backend
and frontend checks, and exercises the synthetic Chromium identity journey. It
does not run the hosted-contract suite or credentialed provider probes; remote
status must be checked after publication.
The [publication runbook](docs/runbooks/REPOSITORY_SETUP.md) records the resolved
disconnect-test failure and passing push/PR CI for `60ef97b`. Each subsequent
commit requires its own CI run.

Default to manual Git commands unless the user explicitly authorizes the assistant to commit/push. The latest user instruction takes precedence. Stop at each completed implementation phase and wait for the user's commit confirmation before beginning the next one. Do not label an unresolved phase complete merely to reach a commit checkpoint.

| Level | Purpose | Status |
|---|---|---|
| Repository check | Local Markdown links, key foundation files, ADR sections/IDs | Available |
| Unit/contract | Diagnostic, identity and hosted adapter behavior | Available; see commands above |
| Build/lint/types | Packaging versus future application checks | Application lint/types/backend packaging and React build available |
| Provider integration | Actual version/account/API compatibility | Phase 0 and feature tasks |
| Evals/load | Quality, cost, stability, and capacity | Separate explicit workloads and budgets |

Do not install custom skills or modify a developer's global Codex configuration merely to contribute. Root instructions link to detailed specifications; add nested guidance only when a real subsystem needs it.

## Licensing

A project license has not yet been selected. Record the owner's license decision and third-party notices before distributing this asset as a reusable licensed release. Do not infer a license from dependencies or the repository URL.
