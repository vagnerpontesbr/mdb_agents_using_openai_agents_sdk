# ADR-0016: Validate agent and CPU ingestion dependencies separately

- Status: Selected for the user-requested dependency validation; local verification scoped
- Owner: Repository maintainer
- Evidence: [Phase 0](../compatibility/PHASE_0.md), [dependency task](../tasks/COMP-001-DEPENDENCIES.md)

## Context

The agent SDK subset runs on Python 3.15.2, but the combined Docling/PyTorch candidate lacks compatible cp315 wheels on the tested macOS ARM64 target. The user authorized Python 3.14 CPU ingestion and subsequently requested dependency validation. Real synthetic PDF/OCR conversion already passed in that separate interpreter.

## Decision

Use two isolated Phase 0 projects under `compatibility/agent-runtime` and `compatibility/ingestion-runtime`, each with its own `pyproject.toml`, `uv.lock`, virtual environment and buildable diagnostic package. Pin exact tested Python patch versions and restrict lock resolution to macOS ARM64, the tested platform. Agent dependencies preserve OpenAI Agents SDK, its voice extra, PyMongo and official Engine memory; ingestion uses Docling and CPU-selected PyTorch. Direct Voyage remains HTTP per [ADR-0015](0015-voyage-http-python315.md).

Pin the `uv_build` backend in both build-system requirements and the locked build group. Build wheel/sdist with `--no-build-isolation` only after syncing that group from the frozen lock. These packages prove dependency/import/build behavior, not an implemented application, deployed worker or provider compatibility.

## Alternatives considered

Downgrade the entire agent runtime; omit PDF/OCR; retain unbounded temporary `uv run --with` environments; or claim cross-platform compatibility from one host. Separate environments preserve the requested agent runtime and the demonstrated CPU parser without those claims.

## Consequences and tradeoffs

Two locks and interpreter installations must be maintained. These narrow diagnostic locks reject untested platforms and Python patch versions intentionally. A future patch/platform migration requires new resolution and behavioral evidence. The future application will add dependencies and its own manifests under FND-003; these locks are not a finished application lock. System Tesseract/Poppler and downloaded Docling model weights remain external to the Python lock. The historical combined candidate remains as failure evidence.

## Validation

Resolve both graphs, sync fresh virtual environments with `--frozen --group build`, verify lock freshness and installed dependency consistency, import required SDK symbols, run a CPU tensor operation, build wheel/sdist using the frozen backend, and repeat synthetic PDF/OCR with the locked ingestion graph. Record exact results in the linked task and Phase 0 evidence. Do not infer Engine service or voice round-trip success from imports.

## Revisit trigger

Revisit when Docling/PyTorch support the agent Python target, when moving to Linux/hosted Engine, or when application dependencies or interpreter patches change. Preserve the selected models and independently validate the hosted runtime.
