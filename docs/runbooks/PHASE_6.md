# Phase 6: Experience and reproducible handoff

Current status and acceptance evidence are in [REL-001](../tasks/REL-001-HANDOFF.md).
The project is MIT licensed; dependencies and hosted services retain their own terms.
This is an independent synthetic telecom reference, not an official MongoDB product.

## Start from a clean checkout

Use Python 3.15.2, uv, and Node >=26.5.0 <27. Preserve the root and frontend locks.
If uv cannot resolve the exact interpreter, follow [Python provenance](../compatibility/PYTHON315_HOSTED.md)
and provide the verified interpreter path. CPU Docling uses its separate Python
3.14.6 environment; it is not installed into the interactive runtime.

```sh
uv sync --frozen --python /path/to/python3.15
npm --prefix apps/web ci
npm --prefix apps/web run build
uv run --frozen python scripts/check_demo_setup.py
uv run --frozen pytest -q
npm --prefix apps/web test
```

For a provider-free browser walkthrough, install Chromium and run the existing
synthetic browser suite. It starts its own loopback server, refuses to reuse an
existing server, and tests identity, support/review/voice flows and document controls.
These tests use synthetic provider responses; they do not certify live integration.

```sh
cd apps/web
npx playwright install chromium
npm run test:e2e
```

## Connect to the approved demo

Copy `.env.example` to ignored `.env` and obtain the scoped credentials privately
from the operator. The application has approved fixed Atlas/Engine targets and a
single synthetic tenant/equipment scope. A clone is not a self-provisioning package
for arbitrary customer clusters. Changing those targets requires the boundary and
role work described in [ADR-0017](../adr/0017-two-cluster-memory-boundary.md).

Follow [application setup](APPLICATION.md) for identity migration/bootstrap only
when needed. Bootstrap does not reset an existing administrator. Use `user` and
`admin`; only the registered information owner can publish governed knowledge.

Set `APP_JOURNEY_ENABLED=true` and `APP_KNOWLEDGE_ENABLED=true` for the full demo.
Required domain credentials and optional cache/voice keys are listed in `.env.example`.
The private operator Engine CLI login remains backend-only. Neither this doctor
nor a local health response verifies credential validity or an unexpired CLI token.

```sh
uv run --frozen --env-file .env python scripts/check_demo_setup.py --configuration
uv run --frozen --env-file .env telecom-api --port 8000
```

Open `http://127.0.0.1:8000` with matching `APP_ORIGIN` and built `APP_WEB_DIST`.

## Demonstrate the behavior

1. Sign in as the demo administrator; inspect account registration. Use a separate
   ordinary account to verify that registration/publication privileges are not implied.
2. Ask for invoice `demo-1`; observe the exact synthetic financial template.
3. Ask for a plan offer, then a simulated change. Inspect the exact proposal and
   approve/reject as its original requester. No real plan or payment changes.
4. Ask for the approved optical procedure. Inspect document/version/page citations.
5. Open knowledge administration and inspect owner, source dates, review deadline,
   status and publication decision. A staged job is not a published document.
6. Follow [Phase 4](PHASE_4.md) for a synthetic PDF replacement: ingestion runs in
   the separate worker, native Engine approval binds the exact action, and current
   source checks reject expired/superseded content. Do not mutate a live source just
   to force a demonstration; use an explicitly prepared synthetic replacement.
7. For voice, use the quiet-environment instructions in [Phase 2](PHASE_2.md).
   Microphone/playback still requires browser permission and human listening.
8. If a request times out, inspect its latest execution before any retry. Runtime
   release is different from deletion of memory/history; memory stays Engine-owned.

## Adapt one tool without deploying it

The business contract is in
[journey_domain.py](../../compatibility/openai_engine_adapter/src/openai_engine_adapter/journey_domain.py).
The SDK orchestration and Engine tool wrappers remain separate. Run:

```sh
uv run --frozen python scripts/check_tool_adaptation.py
```

This copies that module into a temporary directory, changes the synthetic fiber-500
price from USD 89.90 to USD 94.90, verifies the rendered quote, rejects an old price,
and validates the exact simulation receipt. It removes the copy and leaves the
repository and deployment unchanged. This is a business-boundary adaptation trial,
not a native approval or provider compatibility test.

For an intentional real extension, update the typed contract, deterministic domain
rule, wrappers, protected templates, denial/idempotency tests and versioned datasets.
A new remote tool also requires an exact Engine policy/egress proposal; a Python
function alone does not grant tool authority. Preserve requester-bound native review.
For procedure changes, use versioned ingestion/publication rather than editing
published chunks or cached references directly.

## Interpret evidence and package responsibly

[Best practices](../BEST_PRACTICES.md) distinguishes tested controls from future
operations. [Phase 5](PHASE_5.md) records source/candidate metrics, synthetic judge
limits, native token observations and the calibrated candidate cache. Do not call
cache hits prompt-cache savings or claim dollar costs without billing units/rates.

[Publication status](REPOSITORY_SETUP.md) is authoritative for Git/CI; deployed
workflow 8 is distinct from a commit. Load/scaling belongs to Phase 8. This handoff
does not expand the demo's authentication, single-tenant or production-readiness scope.

## Rehearsal evidence

[REL-001](../tasks/REL-001-HANDOFF.md) records the clean automated trial and the requester’s acceptance of it for
this bounded demo. An independent human trial was not performed. At the recorded audit date the runtime dependency audit
was clear; minimatch in development lint tooling had a moderate advisory. Do not run
`npm audit fix --force` blindly: its suggested major downgrades would invalidate the
pinned toolchain. Review and test a compatible remediation separately.
