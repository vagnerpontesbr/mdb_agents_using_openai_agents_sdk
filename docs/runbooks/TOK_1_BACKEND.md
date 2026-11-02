# TOK-1: bounded admin Tokenomics backend

## Behavior and source

Implemented GET `/api/admin/tokenomics/dashboard?period=7d|30d|90d` and
GET `/api/admin/tokenomics/focus-records?period=7d|30d|90d&limit=1..100`.
Default period is 7d. Both endpoints enforce the current application admin principal.
Dashboard authorization is rechecked after the upstream read to reject a revoked
session. Unknown/duplicate parameters and all client scope overrides are rejected.

The backend uses the existing fixed Telecom Engine target and private CLI credential
owner. It configures the adapter only when existing journey configuration is enabled;
there is no new feature toggle, identity, role, secret, collection or trace store.
Startup/login do not read Engine. One refresh performs exactly one GET to the native
cost dashboard, with preview Accept header, 30-second socket timeout, 1 MB body cap,
no redirects, no inference and no automatic retry. Two per-process read slots reject
excess concurrent reads immediately; existing global request admission still applies.
No cache or persistent usage copy is added. Responses have the existing no-store policy.

The native response is parsed through an allowlisted typed projection. Workspace
attribution, token category arithmetic, call coverage, aggregate totals, unique
model/day identities, nonnegative integer counts and row bounds are validated.
Inconsistent/duplicate aggregates are rejected rather than summed or silently
truncated. Native summary, model, workspace and daily totals are parallel views;
none is added to another. Unrecognized fields such as conversations or secrets are
ignored and never returned. Internal project/workspace IDs are not exposed.

## Price semantics and unsupported attribution

[TOK-001](../tasks/TOK-001-TOKENOMICS.md) owns pricing policy. The runtime packages the
reviewed standard short-context rates for the exact observed `gpt-5.6-luna` model;
a deterministic test ties them to the official-price evidence. No compatibility usage
fixture is read at runtime. The single-model source enables the explicitly estimated
uncached input/output scenario, with embedded price provenance and assumptions.
Unknown or multiple-model input/output attribution returns unavailable cost, without
borrowing rates or distributing usage heuristically. Anthropic's approved source
remains usable for a future exact observed model; no Anthropic usage has been found.
Native monetary zero is never interpreted as a billed zero. Voice, embeddings,
tools, gateway fees, historical tariff effectiveness and cache write/read attribution
remain unmeasured. This is not a complete bill or a guaranteed upper-bound estimate.

All TOK-0 dashboard sections are returned. Application, daily, model and token-category
views carry observed counts with partial coverage; exact native period boundary and
internal deduplication semantics are not proven. The returned window is the requested
trailing observation window, not a claim of invoice boundaries. Missing days are
not filled with zero. Execution count, cost/execution, cache ratio, goodput, context,
agent/intent attribution and anomalies explicitly remain unavailable.

Explicit `start`/`end` filters return HTTP 400, code `tokenomics_range_unsupported`:
no native exact historical range contract has been verified. Presets remain supported;
never prorate a trailing period into a historical range. FOCUS returns a reasoned
unavailable page with zero records and no extra upstream read, because the native
source has no event/SKU/invoice endpoint. Cursors are rejected, and limits outside
1..100 fail. This is not a claimed historical filtering or billing implementation.

## Failures and operator recovery

Upstream 401 becomes HTTP 503 / `tokenomics_auth_expired`, preserving the application's
valid login. Native 403/429, timeouts, invalid payloads, oversize responses and capacity
have safe error codes; no provider body, URL or credential is reflected. Native 429
returns application HTTP 429, without automatic retry or invented retry timing.
Missing credentials/unconfigured deployment return unavailable, not sample data.

CLI `auth status` can display a signed-in identity while its access token is expired.
The bounded native `agentengine status` command with the approved explicit workspace
can refresh credentials. The web endpoint never launches a CLI, opens login, changes
credentials or retries as a side effect of page load.

## Validation

45 synthetic adapter/HTTP tests passed: unauthenticated/user denial before source
read; reauthorization after revocation; strict filters; 7/30/90 routing; page bounds;
unknown/multiple-model prices; zero/empty distinction; bad scope/counts/duplicates;
period checks; error sanitization; exact one-GET scope/timeout; 1 MB cap; two-slot
admission/release; no fixture fallback; no startup/focus inference or source read;
price evidence correspondence and unavailable historical filters.

Executed `uv run --frozen pytest -q tests/foundation/test_tokenomics_service.py`.
`uv run --frozen mypy` passed 33 source modules. Initial Ruff found import ordering
and six overlong lines; corrected, final lint passed. No behavioral test assertion
failed. A subsequent import-order finding from the range-error addition was also
corrected before the 45-test rerun passed.

Real source acceptance used `uv run --frozen python /tmp/telecom_tok1_read.py`.
The first request correctly reported expired auth; native CLI status refreshed the
session, then one explicitly repeated read passed. No hidden retry or provider
invocation occurred. [Sanitized evidence](../../compatibility/tok1-source-evidence.json)
records 259,874 observed tokens, USD 0.0811888 estimated, partial coverage, one model
and five daily rows. This proves the real source adapter; HTTP role controls were
validated with local identity fixtures, not a live deployment.

Full regression/build and publication evidence follow below. TOK-2 still owns all
interface rendering and localization; existing support/voice code is unchanged.


Final local gate: `uv run --frozen pytest -q` passed **322 tests** (277 existing plus
45 new); `uv run --frozen ruff check src/telecom_app tests/foundation` passed;
`uv run --frozen mypy` passed 33 modules; `uv build --no-build-isolation` produced
wheel/sdist. `python3 scripts/check_repository.py` passed 99 Markdown files / 34 ADRs;
`git diff --check` passed. Frontend/hosted/identity suites were not rerun locally;
required remote CI executes them before merge. No dependency or frontend files changed.

Scope review found no new memory/trace writer, broad role, provider call, mutation retry
or runtime secret exposure. Missing native attribution stays unavailable. Supported
presets are validated; arbitrary historical-range support remains an explicit feature
limitation, not a claimed passed historical filtering test. Local TOK-1 acceptance is
complete; remote CI/publication remain pending.
