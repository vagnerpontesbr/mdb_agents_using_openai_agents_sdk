# UI-3: Application Control Plane

## Current status

UI-3 is implemented and its explicitly authorized Atlas/persistence gate passed.
Branch codex/ui-3-control-plane is based on LANG-3 merge 856bc60. Publication and
remote CI remain pending. [ADR-0034](../adr/0034-application-control-plane-settings.md)
owns storage/runtime decisions; chronological preparation records below are retained.

## Delivered locally

- Admin overview edits message/query lengths and library cache age within fixed
  ceilings; values are validated server-side and captured for each new operation.
- Concurrent saves compare revisions. A save with uncertain outcome disables further
  writes until explicit reload; no automatic mutation retry.
- An admitted chat continues after a setting changes. A subsequent oversized message
  is rejected before Engine invocation, with an editable draft instead of an uncertain
  execution lock. The initial composer limit is returned by authenticated capabilities.
- Library cache gets a per-request bounded-age view sharing its existing connection;
  source expiry, tenant/ACL and release checks remain authoritative. Hosted cache is
  unchanged and explicitly labeled read-only.
- Capabilities distinguish configured from live health; integration information is
  sanitized and shows mymemory as planned. No inference occurs when loading these pages.
- Users listing is admin-only, uses public fields, stable user-ID pagination and a
  50-row maximum. Existing registration remains in the Users screen.
- English, Brazilian Portuguese and Spanish labels; observed timestamps use the
  profile locale/timezone. No database URI, secret or arbitrary configuration editor.

## Approved Atlas proposal — applied and verified

[Immutable proposal](../../compatibility/ui3-control-plane-proposal.json):
SHA-256 787ce7e4f5adaff4f5b0834ea9d794e6baccbc46ea9c3ca29da492bb83d0d7e2.

Project 67b385a7976edf15ecc62e06, cluster OpenAI-SDK:

1. Create telecom_identity.application_settings with the strict/error validator in
   create_command. One allowed document ID, validated bounded integers and at most
   20 audit entries. No existing document or index changes; MongoDB's automatic _id
   index is implicit.
2. Extend telecomDemoIdentityRuntime with FIND/INSERT/UPDATE on exactly this collection.
   Read-only inventory found one direct consumer, telecom_demo_identity_runtime,
   scoped to OpenAI-SDK. The role itself is project-scoped; recheck consumers/drift
   immediately before mutation. Preserve every existing permission.
3. After resource readback, run an isolated real-identity acceptance with at most
   three configuration saves: initialize defaults, change test values, restore defaults.
   Check revision conflict, normal-user denial and persistence after backend restart.
   Invalid-schema attempts must be rejected without persisting documents. No model,
   voice, embedding or Engine invocation is included. Preserve existing demo servers.

Preparation command (executed, read-only):

    python3 scripts/prepare_control_plane_resources.py

Preflight (executed successfully, no mutation):

    uv run --env-file .env --frozen python scripts/apply_control_plane_resources.py

Mutation command (NOT executed; explicit approval required):

    uv run --env-file .env --frozen python scripts/apply_control_plane_resources.py --apply-approved-change

Only after the live gate, enable APP_CONTROL_PLANE_ENABLED=true for an updated
application. Checked-in default remains false. No private env value was changed.
Role/schema scripts verify proposal hash and baseline before writes, preserve partial
evidence and refuse automatic resumption. Runtime identities never get validator rights.

Rollback: start updated app with APP_CONTROL_PLANE_ENABLED=false, then restore the
reviewed role_before after checking consumers. Retain the settings collection/history.
For value rollback, save old values under the current revision. A rollback does not
rewrite in-flight executions. No source data or managed memory is touched.

## Validation and failures

- 247 foundation tests passed; Ruff and mypy passed (31 modules).
- Frontend lint, 6 unit tests and TypeScript/production build passed.
- Complete browser suite passed 28 tests after fixture corrections; final message-
  rejection test was added afterward and is recorded separately below.
- Visual review of 390px screenshots in English, Portuguese and Spanish found no
  horizontal clipping. Desktop/final visual evidence follows below.
- Read-only MongoDB collection inventory: users, sessions, login_attempts; proposed
  collection absent. Atlas role and direct consumer inventory matched the proposal.
- Hosted adapter unchanged; no hosted deployment or live inference was performed.

Failures and corrections:
1. New pagination test initially failed (missing items), because its in-memory fixture
   read email rather than the actual identity field _id. Fixed the fixture, rerun passed.
2. First full browser run: 23 passed / 3 failed. The added UI test consumed an extra
   real fixture login, causing the existing profile re-login to hit its attempt limit.
   A dedicated synthetic session isolates it without weakening application rate limits.
   Two workspace tests mocked login identity but not the new admin API, which correctly
   returned 401 and cleared the synthetic session. Added explicit API doubles to those
   navigation tests. Complete rerun passed 26, then all 28 with language cases.
3. Ruff reported import order and long lines in new backend/fixture code; corrected.
   Tool-call JavaScript quoting errors occurred before execution and caused no edits.
4. Git/Atlas reads hit sandbox write/DNS restrictions. Required approved retries
   succeeded. No resource mutation was attempted to work around restrictions.


## Final local gate

The final full foundation run passed **247 tests**; Ruff passed and mypy passed
31 modules. Frontend lint/type/build passed; 6 unit tests passed. The final complete
Playwright suite passed **29 tests**, including the added definite-rejection behavior.
Commands: uv run --frozen pytest -q; uv run --frozen ruff check src/telecom_app
tests/foundation; uv run --frozen mypy; npm --prefix apps/web run lint; npm --prefix
apps/web test; npm --prefix apps/web run build; TELECOM_TEST_PORT=53189 npm --prefix
apps/web run test:e2e. Proposal/apply scripts passed isolated Ruff F/I checks.

A final read-only role graph inspection also checked inherited roles: only
telecomDemoIdentityRuntime is affected, with the same one scoped identity consumer.
The proposal was regenerated before approval to include that explicit role graph;
the pinned hash above is authoritative. No mutation has been performed.


Additional final checks: all 7 Control Plane tests passed after adding indirect-role
consumer inventory and no-write-without-apply/drift controls (the prior full suite
had 247 tests). The 15 demo-auth tests passed. The focused browser settings case
passed after adding 1440px visual capture and keyboard Tab focus verification.
Visual inspection of 390px en/pt/es and 1440px desktop captures passed. The final
read-only preflight with inherited-role inventory passed; no Atlas write occurred.
Repository checks passed for 97 Markdown files and 34 ADRs, and diff whitespace
checks passed. Publication/live acceptance remain pending the precise Atlas decision.


## Authorized Atlas and real HTTP acceptance — passed

The requester answered "autorizado" to the exact proposal and bounded three-save
test. Executed the apply command above. [Applied evidence](../../compatibility/ui3-control-plane-apply-evidence.json)
records collection creation, strict/error validator readback and exact role readback.
The immutable proposal retains its draft label and hash as approved input; evidence
records actual execution separately. No other collection, role consumer, index
configuration, memory or Engine deployment was modified.

Executed the private operator helper /tmp/telecom_ui3_acceptance.py with the real
application identity and existing admin/user accounts against an isolated backend
on port 53192. [Live evidence](../../compatibility/ui3-control-plane-live-evidence.json)
records exactly three successful configuration saves: defaults (revision 1), a
temporary 3999-character/300-second-cache setting (revision 2), then restoration of
all defaults (revision 3). A process restart preserved both stored settings and
the authenticated session. Stale save returned 409; normal-user read/write/list
returned 403; admin user listing returned only public fields; malformed insert
failed MongoDB validation code 121 without retaining a document; three atomic audit
events match the three successful saves. No provider calls were made.

The isolated backend was stopped. Existing demo servers were preserved. The private
.env now sets APP_CONTROL_PLANE_ENABLED=true for the next updated application start;
the checked-in default remains false for other unvalidated deployments. The test
helper was kept outside the repository because it consumes private local test
credentials; no secret, cookie, email listing or microphone recording is committed.
All live checks passed without retry or partial application.


## Release validation after live acceptance

The complete foundation suite passed **249 tests** after the resource-preflight
controls were added. Ruff passed; mypy passed for 31 modules; wheel/sdist builds
passed; uv pip check passed for 59 packages. Frontend lint, six unit tests and
TypeScript/Vite build passed after a final error-message correction: a rejected
library query now asks the user to check its query/length instead of PDF metadata.
The earlier complete 29-browser run and focused desktop/keyboard check remain valid;
remote CI will repeat the full suite on the published commit. No live resource or
persistence test failed in this authorized execution. Repository/diff checks passed.
