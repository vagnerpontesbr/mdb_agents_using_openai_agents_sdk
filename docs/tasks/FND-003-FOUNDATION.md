# FND-003: Executable application foundation

- Status: Complete; commit b2ff9c7 published, PR #2 merged, main CI passed
- Owner: Repository implementation
- Phase: 1
- Dependencies: Accepted COMP-001 through COMP-005
- Decision: [ADR-0024](../adr/0024-phase-one-application-boundaries.md)

## Scope and acceptance

The user authorized Phase 1 after publication and merge of Phase 0. Deliver the
React account journey over a packaged same-origin identity API, reusing existing
users and policy. Complete frozen installs, backend/frontend builds, lint/types,
HTTP/security tests, browser tests and documentation. Preserve the exact Python
target and separate ingestion/runtime boundaries; do not begin Phase 2.

## Delivered behavior and files

- Root `pyproject.toml`, `.python-version`, `uv.lock`: installable backend and CLI
  entrypoints, with the existing identity implementation packaged from its source.
- `src/telecom_app`: strict configuration, typed input/output and interpretation/
  outcome contracts, protected invoice rendering, HTTP bounds, identity facade,
  lifecycle-managed MongoDB client and separate index/bootstrap administration.
- `apps/web`: React/TypeScript sign-in, account view, admin registration, logout,
  loading/error states, responsive styling, npm lock and unit/browser tests.
- CI adds an application job with exact interpreter provenance, frozen installs,
  backend lint/types/tests/build, frontend lint/types/unit/build and Chromium
  browser flow. No credentials or live provider calls are required.
- [Application runbook](../runbooks/APPLICATION.md) provides setup/configuration,
  process and namespace ownership, migration semantics and actual commands.

## Tested dependency decisions

Python 3.15.2; FastAPI 0.162.0; PyMongo 4.19.0; Uvicorn 0.54.0; Pydantic 2.14.2;
setuptools 84.2.1; mypy 2.4.1; Ruff 0.17.3; pytest 9.2.0. Exact transitive versions
are authoritative in `uv.lock`.

Node 26.5.0/npm 11.17.0; React 19.3.1; Vite 8.3.5; TypeScript 6.0.3; Vitest 5.0.5;
Playwright 1.64.1; ESLint 10.13.0/typescript-eslint 8.72.1. TypeScript 7.0.2 was
rejected by npm because typescript-eslint requires `<6.1.0`; select supported
6.0.3 without forcing or ignoring peer dependencies. No Python downgrade.

Official contracts checked on 2026-10-29: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[PyMongo pools](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/connection-pools/)
and [Vite setup/build](https://vite.dev/guide/). Pinned installed APIs are exercised
by the tests. Starlette 1.10.0 currently warns that its working HTTPX TestClient
adapter is deprecated in favor of HTTPX2; this warning is not suppressed.

## Validation evidence

Executed on 2026-10-29:

| Check | Result and scope |
| --- | --- |
| Root `uv sync --frozen`, `uv lock --check`, `uv pip check` | Passed on macOS ARM64/Python 3.15.2; 32 installed packages including build/dev dependencies |
| Backend Ruff and strict mypy | Passed; 9 new application source modules checked |
| Foundation pytest | 19 passed on macOS and Linux amd64; negative host/origin/body/role/identity inputs, redacted errors, revoked permissions, throttling, lifecycle cleanup, bounded admission and exact rendering |
| Existing identity/admission suite | 15 passed; unchanged Phase 0 policy implementation |
| Existing compatibility suite | 74 passed; no credentialed provider execution |
| Wheel and sdist | Built successfully with pinned setuptools; wheel installed in a fresh temporary environment and API/config/rendering/session imports and both CLI help entrypoints passed outside the source checkout |
| Linux clean install | Frozen lock installed in a fresh mounted source allowlist using the existing Python 3.15.2 Linux image; Ruff/mypy/19 tests passed with external networking disabled |
| Frontend clean `npm ci` | Passed from package-lock; audit reported zero vulnerabilities at execution time |
| Frontend lint, TypeScript, Vitest, Vite build | Passed; 3 unit tests; final build includes the busy-state input fix |
| Playwright Chromium 156.0.8078.4 | 2 passed against built React and real loopback HTTP with synthetic in-memory storage: admin registration, reload, user login, denied direct registration, HttpOnly cookie, empty localStorage, logout and mobile layout |
| Visual review | Desktop sign-in/admin and mobile sign-in screenshots checked; no horizontal overflow; screenshots remain ignored artifacts |
| Real Atlas check | Authenticated read from the approved application cluster passed using the existing private restricted configuration; no new account, migration or role write |
| Real application startup | Built React entrypoint and `/healthz` served successfully by the Atlas-backed API on loopback port 53182; this is not a live browser account-write test |
| Repository validation | 64 Markdown files/24 ADRs passed; generated tool caches excluded from document checks; `git diff --check` passed |
| Configured-secret scan | No configured private credential value found in tracked/untracked versionable files; values were not printed |

The first browser attempt found an occupied port; tests now use configurable
`TELECOM_TEST_PORT` and never terminate unrelated services. A subsequent test
exposed filling a form before logout completed; the test now waits for the sign-in
screen and the UI disables credential fields during pending operations. The final
build and browser run passed after those changes.

Local Linux checks do not establish a successful remote GitHub Actions run. The
new application job must run after publication. No new model/Engine/OCR calls,
shared policy changes, memory writes or hosted deployments were performed.

## Limits and next checkpoint

No supervisors, specialists, business tool execution, chat/voice, retrieval or
new Engine adapter features are implemented in this phase. The invoice template
is a tested response contract, not a live invoice endpoint. The original bounded
Engine deployment remains unchanged. Public deployment, load sizing and actual
full-journey template enforcement require later phases. Phase 0 demo decisions
remain in force; no new memory/approval/transcript owner is introduced.

Changes are local until explicitly committed/pushed. New GitHub Actions checks
cannot be described as remotely passed before publication. Stop at this phase
boundary and provide manual commit commands before starting Phase 2.

## Publication follow-up

Phase 1 commit `b2ff9c7` was published and PR #2 merged as
`f7611dc7571aef4d76da0c6f8d6069ef85ebd146`. The
[main CI run](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40986600069)
passed. Earlier local-only statements above describe that implementation checkpoint.
The user subsequently authorized Phase 2, tracked in [VERT-001/002](VERT-001-JOURNEY.md).
