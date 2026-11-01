# Running the telecom demo application

The application includes account management, SDK-orchestrated support, browser
voice and governed PDF knowledge. Journey and knowledge are opt-in features.
Use [the Phase 6 handoff](PHASE_6.md) for the current end-to-end setup and demo;
[the Phase 0 demo](DEMO.md) is a historical compatibility harness.

## Prerequisites and frozen setup

Use Python 3.15.2, uv and Node 26.5.0/npm 11.17.0. The Python target is exact; the
approved CPU ingestion environment remains separate. If the installed uv catalog
does not include Python 3.15.2, provide an existing verified interpreter via
`--python /path/to/python3.15`; do not downgrade. The CI workflow downloads and
checks the same upstream Linux distribution recorded in the
[Python provenance](../compatibility/PYTHON315_HOSTED.md).

From the repository root:

```sh
uv sync --frozen --python /path/to/python3.15
npm --prefix apps/web ci
npm --prefix apps/web run build
```

Build dependencies are locked and included in the default `build` group. Runtime
deployments may use `uv sync --frozen --no-default-groups`; development checks need
the default groups. The root package is the application foundation, not the
separate Engine adapter package.

## Private configuration

Use the ignored `.env`, with `.env.example` as the reference:

- `APP_MONGODB_URI`: restricted SRV credentials for the OpenAI-SDK cluster.
- `APP_MONGODB_HOST`: `openai-sdk.qrmdk.mongodb.net`.
- `APP_ORIGIN`: `http://127.0.0.1:8000`.
- `APP_WEB_DIST`: `apps/web/dist`, produced by the frontend build.

The URI must not contain a database path or unsupported/insecure options. The
allowed query options are `authSource`, `retryWrites`, `appName`, `w` and
`tls=true`. Never substitute the broad diagnostic `MONGODB_URI`. The API does not
load `.env` implicitly; `uv --env-file` injects it. No frontend environment
variable contains credentials. Identity-only mode needs no Engine/model credentials. Full journey, voice and
knowledge prerequisites are in [the handoff runbook](PHASE_6.md).

## Identity indexes and initial administrator

Existing Phase 0 users, sessions and indexes are reused. There is no automatic
reset or migration at server startup. Migration v1 ensures a unique `user_id`
index on `users` and expiry indexes on `sessions` and `login_attempts`; normalized
email uniqueness already comes from `_id`. TTL deletion is not session validity:
the backend checks expiry when reading a session.

For initial setup, using the approved identity administration credential:

```sh
uv run --frozen --env-file .env telecom-admin migrate --apply
uv run --frozen --env-file .env telecom-admin bootstrap --apply
```

Bootstrap asks for the initial administrator password twice without echoing it.
An existing `admin@mongodb.com` account is left unchanged. Normal users are
created by an authenticated administrator in the UI; `user` cannot self-promote
or create another account. Exact role grants remain in
[COMP-005](../tasks/COMP-005-DEMO-AUTH.md#restricted-application-identity-passes).
The current demo credential retains its approved collection-level CREATE_INDEX
grant; separating the command does not claim that Atlas grants were changed.

## Run and use

```sh
uv run --frozen --env-file .env telecom-api --port 8000
```

Open `http://127.0.0.1:8000`. Sign in and use Support/Knowledge in the workspace
navigation. As administrator, open Control Plane → Users to create a synthetic
account. Refresh to verify session restoration; use Profile → Sign out.
Navigation preserves the conversation; leaving Support discards local microphone
recording and stops playback. Profile supports name, IANA timezone and interface language (English, Portuguese
Brazil or Spanish). Inline language selection in Profile preserves active conversation
and audio objects. Profile photo supports JPEG/PNG up to 2 MiB, normalized privately on the backend;
use Choose photo or Remove photo. Password editing and other Control Plane views
remain planned.
Agent response and speech localization remain separate phases; current voice still
expects English. The runtime role now includes UPDATE only on telecom_identity.users
for profile persistence; see UI-001 for verified scope and rollback. Ordinary users see their
account without administration controls; the backend independently denies a
forged registration request. Re-login revokes the browser's previous session.

The server binds `127.0.0.1` only, does not trust forwarded client identity, and
requires an exact Host and same-origin JSON writes. It admits at most eight
application requests, enforces route-specific body limits and waits at most ten seconds for a
body. Authentication persistence is MongoDB-backed, not per-process memory.
`/healthz` is a liveness endpoint after a successful startup connection check;
it does not continuously certify Atlas or Engine health. API/database errors
produce redacted responses; uncertain writes are not retried by the frontend.

Development hot reload is optional: use `APP_ORIGIN=http://127.0.0.1:5173` for the
API while keeping `telecom-api --port 8000`, and run `npm --prefix apps/web run dev`.
Vite forwards `/api` and `/healthz` without changing the browser Host or Origin.
The release acceptance flow uses built static files from the API itself.

## API contract v1

| Method/path | Authentication / result |
| --- | --- |
| `GET /healthz` | Public loopback liveness; service/contract version only |
| `POST /api/login` | Exact email/password input; HttpOnly cookie and public principal |
| `GET /api/me` | Valid unexpired session and active current role required |
| `POST /api/users` | Current administrator required; email/password and optional user/admin role |
| `POST /api/logout` | Revoke the current token; remove browser cookie |

Errors are `{ "error": "..." }`: 400 invalid input, 401 unauthenticated, 403
forbidden, 409 duplicate account, 413 oversized body, 429 throttled login, 503
unavailable/busy. Unknown fields cannot supply tenant, requester or approval
authority. Public identity fields are only `user_id`, `email` and `role`.

## Checks

```sh
uv run --frozen ruff check src/telecom_app tests/foundation
uv run --frozen mypy
uv run --frozen pytest -q
uv pip check
uv build --no-build-isolation
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
cd apps/web
npx playwright install chromium
npm run test:e2e
```

The browser suite launches its own loopback server and synthetic in-memory
identity store. It never reads `.env`, connects to Atlas or calls Engine/OpenAI.
It uses port 53181 by default; set `TELECOM_TEST_PORT` for a different unused port.
Existing servers are never reused or terminated. Screenshots go to ignored
`test-results`. This is browser/HTTP behavior evidence, not live Atlas write or
provider integration evidence. Continue using the separate Phase 0 suites for
the existing identity policy and hosted adapter.

## Ownership and remaining work

[ADR-0024](../adr/0024-phase-one-application-boundaries.md) defines current process,
database and template boundaries. Before increasing replicas or concurrency,
monitor pool checkout failures/waits, connection creation/churn and aggregate
Atlas connections; include monitoring sockets and other shared workloads. Tune
only with measured evidence. No load or public-deployment claim follows from
these foundation checks. Phases 2–5 have bounded acceptance recorded in their task files.

## Phase 2 support journey

The supervisor/specialist and browser voice implementation is opt-in and has passed bounded
hosted/browser acceptance. Follow [the Phase 2 runbook](PHASE_2.md) for the deployment gate,
`APP_JOURNEY_ENABLED`, protected endpoints and recovery. Keep it disabled against
the Phase 0 invoice deployment.
