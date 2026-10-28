# COMP-001-DEPENDENCIES: Locked local SDK and CPU ingestion environments

- Status: Done for macOS ARM64 dependency/install/build validation
- Owner: Repository maintainer
- Dependencies: Python 3.15.2 and 3.14.6, uv, package access
- Relevant ADRs: [ADR-0016](../adr/0016-split-compatibility-environments.md), [ADR-0015](../adr/0015-voyage-http-python315.md)

## Scope

Resolve, freeze, install and build two minimal diagnostic packages without scaffolding application services. Agent Python stays 3.15.2; the authorized CPU ingestion environment uses 3.14.6. The two locks explicitly target macOS ARM64 only.

## Acceptance criteria

- Independent uv locks include all transitive dependencies and the pinned build backend.
- Fresh frozen installs pass, installed versions match the locks, and `uv pip check` reports no incompatibilities.
- Agent/voice/Engine/PyMongo imports and the ingestion CPU tensor check pass.
- Wheel and sdist builds pass using the locked backend; imports from the built wheels pass.
- Actual textual/scanned PDF conversion with page provenance passes again in the locked ingestion environment.

## Validation plan

Run the commands below from the project root. Set `AGENT_PYTHON` to an installed Python 3.15.2 interpreter; this session used `/tmp/telecom-python-manual/python/bin/python3.15` because uv 0.11.3's download catalog did not recognize 3.15.2. This temporary interpreter path is not embedded in the locks.

```bash
export AGENT_PYTHON=/path/to/python3.15
uv lock --project compatibility/agent-runtime --python "$AGENT_PYTHON" --check
uv lock --project compatibility/ingestion-runtime --python 3.14.6 --check
uv sync --project compatibility/agent-runtime --python "$AGENT_PYTHON" --frozen --group build
uv sync --project compatibility/ingestion-runtime --python 3.14.6 --frozen --group build
uv pip check --python compatibility/agent-runtime/.venv/bin/python
uv pip check --python compatibility/ingestion-runtime/.venv/bin/python
compatibility/agent-runtime/.venv/bin/python -c 'from telecom_agent_runtime_probe import check; print(check())'
compatibility/ingestion-runtime/.venv/bin/python -c 'from telecom_ingestion_runtime_probe import check; print(check())'
uv build --project compatibility/agent-runtime --python compatibility/agent-runtime/.venv/bin/python --no-build-isolation --out-dir artifacts/compatibility/build/agent
uv build --project compatibility/ingestion-runtime --python compatibility/ingestion-runtime/.venv/bin/python --no-build-isolation --out-dir artifacts/compatibility/build/ingestion
compatibility/agent-runtime/.venv/bin/python -m unittest discover -s tests/compatibility -v
uv run --no-project --with ruff==0.14.0 ruff check compatibility/agent-runtime/src compatibility/ingestion-runtime/src
```

For the PDF behavior check, first generate the fixtures using the [PDF task](COMP-001-PDF.md) instructions, then run:

```bash
compatibility/ingestion-runtime/.venv/bin/python scripts/check_docling_pdf.py --allow-model-downloads --output artifacts/compatibility/docling-pdf-locked.json
```

## Evidence and handoff

On 2026-10-28 with uv 0.11.3, both fresh frozen installs, offline lock freshness checks, dependency consistency checks, imports, CPU check, wheel/sdist builds and locked PDF conversions passed. The 22 harness tests and Ruff check of the two new packages passed. A separate wheel import check loaded each module directly from its built wheel and compared every installed package version to its lock; see [machine-readable evidence](../../compatibility/dependency-evidence.json) for hashes and package counts. Repository link/ADR checks and `git diff --check` were run after documentation updates.

The agent graph contains 46 packages and ingestion contains 105, including the local diagnostic package and build backend. They are dependency proofs, not application builds. Linux, hosted Engine, browser voice, OS tools and model-weight reproducibility are not covered by the Python locks. No paid provider request or database write was needed for this task. Files and locks are locally authored, not committed/pushed; Phase 0 remains open for provider gates. FND-003 will create application/frontend manifests and CI when those components are implemented.
