# UI-001: Profile navigation and application Control Plane

- Status: UI-0 through UI-2c merged; LANG-3 bounded demo accepted, publication pending; UI-3 next
- Owner: Telecom demo maintainer
- Requested: 2026-11-01
- Branch: `codex/ui-profiles-control-plane`
- Base: `e524a57057f69f7375c921d3077ac6d1045a663d` (`main`, merged PR #4)
- Dependencies: FND-003, VERT-001/002, RAG-001, REL-001, OPS-001
- Relevant ADRs: [0020](../adr/0020-demo-email-password-auth.md), [0018](../adr/0018-engine-feature-precedence.md), [0030](../adr/0030-ui-profiles-control-plane.md)

## Outcome and scope

Replace the single long account/support/knowledge page with a responsive workspace,
a profile menu in the header, and an admin-only application Control Plane. Preserve
the accepted chat, voice, knowledge and requester-bound approval behaviors.

This is a new UI improvement cycle (UI-0 through UI-4), not a reopening or renumbering
of the completed demo phases 0–8. Production capacity and pricing proof remain
outside acceptance. This plan does not authorize new live provider experiments,
infrastructure, credentials, roles, or changes in Engine ownership.

The requester confirmed display name, timezone, language, photo and password change.
Portuguese (Brazil), English and Spanish are required for UI, responses and audio;
[I18N-001](I18N-001-MULTILINGUAL.md) owns the cross-channel contract. The requester also confirmed editable Control Plane configuration. The confirmed editable catalog is limited to application limits and retrieval-cache settings, applied explicitly to subsequent operations without a restart/deploy button;
this is not authorization to edit every Engine setting or credential.

## Reference inspected

Local reference: `/Users/vagnerpontes/Documents/SDD/clientes/fiserv/gensdd-main`.
The files below were inspected read-only; no reference application code, credentials,
branding, datasets or configuration is copied into this repository.

| Reference file | Observed pattern | Telecom adaptation |
| --- | --- | --- |
| `frontend/src/App.tsx` | Sidebar, grouped navigation, header profile and admin routes | Responsive workspace with support, knowledge and admin navigation |
| `frontend/src/components/ProfileMenu.tsx` | Name/avatar, preferences, timezone and sign-out | Photo/initials, account/role, confirmed name/timezone/language preferences, password change and sign-out |
| `frontend/src/components/ControlPlanePanel.tsx` | Categorized tabs, source indicators, loading/error states, save/reset | Categorized application settings with admin editing; integration health remains a read-only observation |
| `frontend/src/components/UsersPanel.test.tsx` | Dedicated user-management test location | Separate user administration tests and direct API denial cases |
| `docs/ADR_004_Credenciais_Providers_Control_Plane.md` | Secret-management functionality in the reference | Not adopted: this demo retains injected secrets and Engine-owned platform capabilities |

The reference also has languages, provider-secret editing, embedding changes and
other domain-specific features. They are not implied by using it as a UI reference.
Developer documentation and source identifiers remain English. User-facing UI,
response templates, fixtures and audio support pt-BR, en-US and es-ES under ADR-0032.

## Proposed navigation and permission matrix

```text
Header: Telecom workspace                 [Initials / Profile menu]
Profile menu: My profile | role (read-only) | Sign out

Workspace navigation
  Support                 #/support
  Knowledge               #/knowledge
  Control Plane (admin)
    Overview              #/control-plane/overview
    Users                 #/control-plane/users
    Capabilities          #/control-plane/capabilities
    Integrations          #/control-plane/integrations
    Tokenomics            #/control-plane/tokenomics
```

`#/profile` is available to both roles. Use fixed hash routes initially to support
reload/back/forward with the existing static-file server, without introducing a
router dependency or a catch-all that can mask `/api` errors. Unknown routes show
an explicit not-found state with a link to Support. Login stays outside the shell.

| Operation | user | admin | Backend authority |
| --- | --- | --- | --- |
| Read/edit own name/timezone/language/photo | Yes | Yes | Session-derived user ID; exact field allowlist |
| Read own email/role | Yes | Yes | Existing authenticated principal |
| Change own password with current-password verification | Yes | Yes | Reauthentication, rate limiting and session invalidation |
| Change own role/email from profile | No | No | Reject privileged/unknown fields |
| List/create users | No | Yes | Existing admin policy, new bounded listing contract |
| View Control Plane | No | Yes | Admin enforcement on every new endpoint |
| Support/knowledge use | Existing permissions | Existing permissions | Existing scope and validity checks |
| Publish documents | Registered information owner only | Registered information owner only | Admin does not imply information ownership |
| Approve an action | Original requester only | Original requester only | Native Engine approval plus backend checks |
| Change secrets/models/memory/policy | Not included | Not included | Existing ownership and private operations retained |

## Current code constraints

- `apps/web/src/App.tsx` mixes login, account registration and the main workspace.
  Extract the shell/profile/registration views without duplicating authentication.
- `Journey.tsx` holds conversation, stream, recovery, recording and audio state.
  Unmounting currently aborts transport and stops audio. Navigation must not silently
  restart a turn or imply remote cancellation. Keep journey state owned above routed
  views; stop microphone/playback explicitly on leaving Support, preserve execution
  identity and show recovery when the outcome is uncertain. Logout destroys user state.
- `Knowledge.tsx` mixes browsing and curator work. Keep the current source/owner
  checks; do not move document publication under generic admin authorization.
- `/api/me` exposes only user ID, email and role. Profile persistence and listing
  users require backend contracts; displaying a new form alone is not completion.
- `/healthz` is liveness; `/api/capabilities` is configuration availability. Neither
  proves ongoing Atlas/Engine/provider health. Label configured, unavailable, unknown
  and verified states distinctly; never render a green health badge from presence alone.
- `api.ts` currently assumes GET or POST and has operation-specific error messages.
  Extend typed parsing and error mapping for new endpoints, including stale profile
  conflicts, rather than reusing the account-registration 409 message.

## Proposed contracts and data changes

These are design targets, not implemented endpoints.

- `GET /api/profile`: own email/role (read-only), display name, IANA timezone, locale, safe avatar metadata and
  profile revision. Existing users without preferences receive documented defaults.
- `POST /api/profile`: only `display_name`, `timezone`, `locale`, `expected_revision`; derive
  identity from the session. Reject extra fields, stale revisions and invalid input.
  Proposed limits: trimmed name 1–80 characters, valid IANA timezone; default timezone
  UTC. Timezone changes affect UI timestamp presentation, not financial templates,
  stored UTC dates, approval expiry, or document eligibility.
- `GET /api/users?cursor=...&limit=...`: admin-only, maximum 50 rows, stable pagination,
  public projection only. Reuse existing `POST /api/users` for account creation.
  No password hashes, cookies, tokens or unrestricted user-document serialization.
- `GET /api/admin/control-plane`: admin-only, explicit allowlisted response for
  application capabilities and nonsecret integration/configuration provenance.
  Do not return environment dumps, connection strings, raw provider errors or secrets.
  Include observation time and distinguish configuration from live verification.
  Loading the page makes no model calls and does not poll providers in the background.

Propose additive profile fields on `telecom_identity.users`; do not create a second
identity database or reset existing users. UI-0 must verify the current document
shape, roles and migration needs. Reuse the authorized identity owner. Prepare any
needed schema/privilege change as an exact migration proposal before a live write;
no broad credential may be introduced to make the feature work.

Configuration editing is confirmed scope. Before implementation, define an exact
allowlist, authoritative owner, validation, concurrency/version checks, audit,
rollback and runtime reload behavior before implementing it. Engine secrets,
memory, approval, tracing and policy remain Engine-owned; editing them requires
separate supported integration evidence, not a generic settings form.

## Phases and quality gates

The requester now authorizes agent-performed commits, branch pushes and PR creation
without additional confirmation, superseding manual-publication instructions.
[AGENTS.md](../../AGENTS.md) owns the delivery workflow: one reviewed phase per PR,
required quality/CI gates before the previously authorized automatic merge, then
the next branch from integrated main. Stop for material unresolved decisions and
Atlas mutations that could affect other projects; do not bypass branch protections.

| Phase | Deliverable and expected files | Required gate | Rollback |
| --- | --- | --- | --- |
| UI-0 — Design and baseline | This plan, ADR-0030 proposal, navigation wireframes, permission matrix, scoped API/data design; inspect `App.tsx`, `Journey.tsx`, `Knowledge.tsx`, identity store and current tests | Verify reference mapping and defaults; record existing test baseline and exact commands; inventory migrations; no UI or remote changes represented as done | Documentation-only revert |
| UI-1 — Workspace shell | `App.tsx`, new `WorkspaceLayout`, navigation/profile-menu components, CSS, focused component/browser tests | user/admin menus, deep link/reload/back, unknown routes, keyboard/Escape/focus, mobile navigation; sign-out and expired session; chat/voice/review/knowledge regressions pass; no lost or duplicate turn on navigation | Revert shell commit; existing backend contracts unchanged |
| UI-2 — Full profile (subphases below) | New profile view and backend module, `contracts.py`, `identity.py`, identity persistence, `api.ts`, migrations only if required | Save/read after reload and new login; existing users migrate safely; two-user isolation; role/email injection rejected; stale update returns 409; invalid timezone and text rejected; escaping and UTC business rules preserved | Additive preferences remain harmless to old code; revert feature without deleting users |
| UI-3 — Admin Control Plane | New Control Plane and Users views, typed admin API, bounded listing, registration moved into Users | direct API and route denial for user; admin list/create; empty/error/timeout states; no secrets in responses/logs; configured is not healthy; no provider calls on page load; no duplicate create on uncertain response | Revert UI/API phase; preserve created users and existing private config |
| UI-4 — Integration and handoff | Cross-feature browser tests, focused visual evidence, current README/runbook, consolidated acceptance table | All local/CI gates pass; user/admin walkthrough; 390px and 1440px layouts, keyboard/focus and 200% zoom; clean-checkout startup instructions; final review against actual diff and accepted scope | Revert the affected UI commit(s), keep identity/documents/Engine data intact |

UI-1 may expose a clearly labeled admin placeholder until UI-3, but no fake status,
user list or successful action. UI-2 and UI-3 may only claim persistence after backend
and permission tests pass. UI-4 is the acceptance boundary for the whole improvement.

### Gate rules

1. Every agreed acceptance scenario must pass; failing or unrun checks block that
   phase, not silently turn into exceptions. Record pre-existing failures separately.
2. No unresolved critical/high finding, authorization regression, secret exposure,
   lost approval association or duplicate business invocation. Medium findings need
   an explicit disposition in the task record before acceptance.
3. Test public behavior, invalid inputs and cross-user/role cases. A snapshot or
   element-exists assertion alone does not prove backend authorization or persistence.
4. No blanket retries or sleeps to hide flaky tests. Fix the cause and rerun the
   affected checks. Tests must not reuse or terminate an existing demo server.
5. Visual verification checks overflow, selected states, labels, contrast, focus and
   loading/error/empty states. Retain synthetic screenshots with no credentials or
   personal data; screenshot approval does not replace functional tests.
6. Final reviewer reads the diff and compares claims with evidence. CI green is not
   treated as independent code review. Record commit, files, checks/results, known
   limits and manual verification in the table below.

### Commands planned for implementation verification

```sh
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e
uv run --frozen ruff check src/telecom_app tests/foundation
uv run --frozen mypy
uv run --frozen pytest -q
python3 scripts/check_repository.py
git diff --check
```

Run frontend checks for each UI implementation phase and backend checks whenever
backend/contracts or fixture boundaries change. Run the full existing and new suites
at integration. If an Engine adapter contract is touched, also run the pinned hosted
contract suite; otherwise do not rebuild/redeploy Engine for a navigation change.
Test fixtures remain provider-free; any later live check is bounded and separately
reported. No repeated load, pricing or production-capacity proof is part of this UI work.

## Evidence and handoff

| Phase | Code status | Validation evidence | Publication |
| --- | --- | --- | --- |
| UI-0 | Design and migration inventory complete; requester decisions recorded | Local and remote gates passed | PR #5 merged as `f43a10f` |
| UI-1 | Responsive workspace, profile disclosure, fixed routes, preserved journey | Local gates and 332 remote tests passed | PR #6 merged as `95d2982` |
| UI-2 | UI-2a and UI-2b merged; UI-2c password implemented | Local UI-2c gates passed | PR #8 merged as `9f466e5`; UI-2c publication pending |
| UI-3 | Not started | Not run | None |
| UI-4 | Not started | Not run | None |

Planning checks must not be reported as UI acceptance. Baseline from the preceding
review: 138 backend tests, Ruff, mypy and repository checks passed; PR #4 was merged.
That is historical evidence, not a fresh browser baseline for this improvement.

Planning validation (2026-11-01): the repository checker passed 85 Markdown files
and 30 ADRs after correcting the proposed ADR's required section heading;
`git diff --check` passed. No application tests, visual acceptance, provider calls,
database writes, commits or pushes were performed for this documentation-only plan.

## Requested additions — 2026-11-01

[TOK-001](TOK-001-TOKENOMICS.md) adds the Fiserv-inspired Tokenomics menu and
Overview/Breakdown/FOCUS dashboards, with admin-only access and tested data semantics.
The expanded UI-4 acceptance requires TOK-3 to pass. Missing prices remain unavailable;
usage dashboards do not reopen the waived billing/production-capacity proof gates.

[MEM-002](MEM-002-MYMEMORY-MIGRATION.md) plans the independent migration of Engine
memory to mymemory, with tests after every change. Integrations shows current versus
planned destination from sanitized verified metadata, never a URI. If migration
ships later, label it planned; only MM-4 acceptance can mark mymemory active.
Never combine a UI rollout and a memory cutover. No migration button or secret
editor is added. Changes to the DemoTelco project remain later work.

## Confirmed profile scope and UI-2 subphases

Each subphase gets its own tests, commit and PR under the current AGENTS.md workflow.

| Subphase | Deliverable | Required tests |
| --- | --- | --- |
| UI-2a | Display name, timezone, pt-BR/en-US/es-ES preference; integrate LANG-1 catalogs | Persistence across login/reload, existing-user defaults, invalid locale/timezone, stale revisions, cross-user denial and protected role/email fields |
| UI-2b | Add/replace/remove own photo; initials fallback | Server-side file decoding, MIME/content mismatch, image dimensions/size bounds, malformed/truncated files, disallowed SVG/animated content, metadata removal, safe thumbnail encoding and other-user denial |
| UI-2c | Change own password using current password, new password and confirmation | Wrong current password, password policy, rate limits, atomic change, all old sessions invalidated, new login, concurrent sessions, no password/hash logging or browser persistence |

Photo processing must be bounded before decoding and normalized on the backend;
client resizing is convenience, not validation. Specify exact upload/pixel/thumbnail
limits and a scoped private storage contract in UI-0. Current middleware accepts
JSON and bounds bodies: design an explicit avatar route/body limit with matching
tests rather than weakening global limits. Do not accept remote avatar URLs, render
untrusted SVG, or copy arbitrary image data into the principal response. Use safe
raster content with explicit content type and private/no-store behavior. Any image
library must be justified, pinned, locked and tested before introduction.

Password changes use a separate authenticated endpoint and the existing hashing
policy. Derive the account from the session; never accept a target user/role.
Require current-password verification and prevent brute-force attempts. Choose a
transaction or checked credential-version scheme to make password replacement and
old-session rejection effective together, including concurrent requests. Require a
fresh login after success; the UI must not claim success on an uncertain response.
No forgotten-password email flow or administrator password reset is included.

LANG-2 and LANG-3 are mandatory before expanded UI-4: translated screens alone do
not meet the confirmed multilingual agent/audio requirement. All photo and password
errors, confirmations and accessibility labels are localized in the three catalogs.

## Confirmed editable Control Plane and remaining decisions

The requester confirmed that Control Plane permits configuration changes. Editing
is admin-only and enforced server-side, with typed allowlisted fields, validation,
expected revision, sanitized audit metadata and explicit success/conflict/failure
states. UI-3 must include mutation and permission tests, not merely read endpoints.
Client-provided arbitrary keys, database names, hosts or roles are not allowed.

The requester confirmed both decisions on 2026-11-01:

1. Edit only bounded application limits and retrieval-cache settings within fixed
   safety ceilings. Feature toggles remain read-only. Provider secrets, model and
   embedding selection, Engine policy and memory administration are excluded.
2. An explicit Save/Apply affects subsequent operations. In-flight executions retain
   their captured configuration; saving must not restart, cancel or reinterpret them.
   No restart/deploy button is included. Fields that cannot be safely applied at
   runtime remain read-only with their activation requirement clearly displayed.

UI-3 must map the actual fields to their authoritative owners and fixed safety
ceilings, validate them server-side and test revision conflicts, invalid values and
in-flight configuration snapshots. These implementation checks do not authorize
shared Atlas mutations.

The shared-project memory decision is conditional on MM-0 inventory: if moving the
current Engine project affects DemoTelco now, ask whether to coordinate all consumers
or design a separate Engine project. Do not treat this unverified condition as an
already required project split. Preserve existing memories by default.


## UI-0 baseline and implementation constraints — 2026-11-01

Implementation was requested. The current branch remains `codex/ui-profiles-control-plane`.
The baseline below was executed against the existing application before UI changes.
No Atlas mutation, hosted deployment or new provider inference was performed.

### Executed checks

| Command | Result | Coverage / limit |
| --- | --- | --- |
| `npm --prefix apps/web run lint` | PASS | Frontend ESLint |
| `npm --prefix apps/web run typecheck` | PASS | Frontend TypeScript |
| `npm --prefix apps/web test` | PASS, 3 tests | Identity parsing, sanitized errors/no write retry, unauthorized status |
| `npm --prefix apps/web run build` | PASS | TypeScript and production Vite bundle |
| `TELECOM_TEST_PORT=53189 npm --prefix apps/web run test:e2e` | PASS, 10 tests on rerun | Identity/session reload/logout, mobile sign-in, exact approve/reject, uncertain-call recovery/no duplicate submission, microphone denial, synthetic WAV playback, pending-review reload, native-review curation UI doubles |
| `uv run --frozen ruff check src/telecom_app tests/foundation` | PASS | Only the configured application/foundation scope |
| `uv run --frozen mypy` | PASS, 27 source files | Application typing; not full hosted adapter typing |
| `uv run --frozen pytest -q` | PASS, 138 tests | Existing foundation behavior/contract suite with local doubles |
| `python3 -m unittest discover -s tests/compatibility -v` | PASS, 75 tests | Probe harness, evidence controls and provider-free contracts |
| `python3 -m unittest discover -s tests/demo_auth -v` | PASS, 15 tests | Authentication, sessions, requester-only Engine admission, revoked-role/session denial |

Browser failure explanation: the first attempt could not start the fixture server
because the sandbox denied access to the uv cache. No browser test ran in that
attempt. Rerunning with the required execution permission started an isolated server
on port 53189, with `reuseExistingServer: false`; all 10 tests passed. This was an
environment failure, not evidence of an application regression. Playwright emitted
an informational NO_COLOR/FORCE_COLOR conflict warning; it did not fail a test.

These are local results, not a new GitHub CI run. Hosted-contract tests, live Atlas
role/schema inspection, real multilingual voice listening and new-screen visual
acceptance have not been run in this phase. Existing browser doubles do not prove
provider compatibility or real speech quality. Remote required CI remains a separate
publication gate.

### Design and migration inventory

- Desktop wireframe: header with profile menu, left grouped navigation, main route
  content. Mobile: header with navigation toggle, dismissible navigation, full-width
  content. Support remains mounted under the authenticated workspace with stable
  user identity; route visibility must not reset execution, draft or messages.
  Language selection must not trigger the leave-Support audio cleanup. Logout still
  clears user state. Keyboard Escape returns focus to the opening menu button.
- Inspection of `compatibility/demo_auth/auth.py`, `sessions.py` and `mongo.py`
  confirms existing user records contain normalized email ID, user ID, role, active,
  password hash and schema version. Sessions currently contain hashed token ID,
  email, user ID and expiry; there is no credential-version rejection yet.
- UI-2a requires additive profile persistence and revision checks with legacy defaults,
  not a bulk user replacement. UI-2c requires atomic credential replacement and a
  checked session credential version, including login/password-change race tests.
  Existing live validators and privileges remain unverified; inventory them before
  proposing any Atlas migration. Ask before changes that may affect other projects.
- UI-2b design limits: JPEG/PNG input only, maximum 2 MiB encoded body, maximum
  4096 pixels per side and 4 million decoded pixels; reject animation, malformed
  files and decompression bombs. Normalize to a metadata-free thumbnail no larger
  than 256 by 256 and 128 KiB. Select a supported pinned decoder during UI-2b.
  Store only the bounded normalized image under application-owned identity scope;
  exact persistence/migration contracts need implementation review. Do not weaken
  the global JSON body limit or expose a public bucket/remote image URL.
- Existing reference mapping, navigation outline and permission matrix above remain
  the design basis. No new endpoint or UI component is represented as implemented.

### Gate disposition

The requester approved the restricted catalog (application limits and cache only)
and subsequent-operation Save/Apply semantics, without restart/deploy controls.
The UI-0 local design/baseline gate is complete. Publication and required remote CI
remain pending; UI-1 has not started. Actual-cost source discovery remains TOK-0
work; no access or actual monetary coverage is inferred from this baseline.


## UI-1 implementation and evidence — 2026-11-01

UI-0 was published in PR #5 and merged as `f43a10f04304d8f9687a273922c8c4b83141ae5a`.
Both repository/application jobs passed in runs `41309363443` and `41309381580`.
UI-1 starts from that integrated main on `codex/ui-1-workspace`.

Implemented a responsive WorkspaceLayout with fixed hash routes, profile disclosure,
keyboard Escape/focus return, skip link, selected navigation and mobile disclosure.
Existing account creation moved into the admin Users route; no new backend endpoint
or privilege was added. Profile editing and other Control Plane views are explicitly
pending. Unknown routes and forbidden admin routes have separate views.

Journey remains mounted above route visibility: messages, draft, conversation ID,
transport and pending action survive navigation. Leaving Support cancels local
recording and pauses playback, but does not cancel accepted work. Late microphone
permission or audio responses cannot start capture/playback while Support is hidden.
Authenticated 401 responses clear the current workspace; initial login/session checks
are excluded from the expiration event. No provider/Atlas changes were made.

### Local validation

- Frontend ESLint, TypeScript and production build passed.
- Vitest: all 3 existing API contract tests passed.
- Playwright: all 15 browser tests passed (10 regression and 5 workspace tests).
  New coverage: draft/conversation preservation during an in-flight request with
  exactly one invocation; deep-link/reload/back/forward; user denial for admin routes;
  unknown routes; mobile and keyboard disclosures; expired-session cleanup;
  exact pending approval after navigation; no late offscreen audio playback.
- A focused rerun of the keyboard/layout case passed after adding 200% CSS zoom
  coverage. Desktop 1440px, mobile 390px, narrow 720px reflow and CSS zoom 2 were
  inspected; no clipping/overlap was found. CSS zoom is recorded explicitly, not
  claimed as a manual browser-menu zoom test.
- Screenshots are generated under ignored `apps/web/test-results`; only synthetic
  fixture identities are used. They are local visual evidence, not hosted screenshots.
- Two non-escalated browser attempts could not initialize uv's cache in the sandbox;
  no tests started in either attempt. Permission-enabled reruns passed. This is an
  environment failure, not a failed behavior assertion. No behavioral test failed.
- Backend source is unchanged. The UI-0 backend baseline is historical; remote CI
  reruns backend and hosted-contract suites before integration. No live voice,
  Atlas schema/roles or multilingual provider test is represented as performed.

Review disposition: no unresolved critical/high finding in the scoped diff. User/admin
menu restrictions complement the unchanged backend authorization; UI route checks
alone are not claimed as backend permission proof. No routes expose configuration,
secrets, invented cost/health values or a second memory owner. Subsequent UI-2/LANG
work must preserve the mounted journey and the existing action/session identities.


## UI-2a current implementation and remote gate — 2026-11-01

Branch `codex/ui-2a-profile` starts from merged UI-1 (`95d2982`). Implemented
session-derived GET/POST `/api/profile`, strict field validation, IANA timezone and
three-locale allowlists, bounded names, protected identity fields and revision-based
atomic updates. Legacy defaults are display name `User`, timezone `UTC`, locale
`en-US` and revision 0; reading old accounts does not write or migrate them.
Profile fields are embedded in existing identity documents; no new collection,
index, Engine writer or schema reset is introduced. The update uses dotted fields
to preserve future independent profile attributes.

The profile form and inline profile-menu language selector persist through the API.
Inline switching preserves the mounted journey, draft, execution, approval and audio
objects. User preference wins after login; unauthenticated locale selection is
in-memory. Interface catalogs cover login, profile, navigation, support controls and
knowledge controls in en-US/pt-BR/es-ES. Timestamps use the selected timezone and
numbers use locale formatting without currency conversion. Raw source metadata,
provider prose and historical messages remain unchanged. Typed safe UI errors are
localized without matching arbitrary exception text or exposing provider details.

This is interface localization only: LANG-2/3 hosted response and speech propagation
are not implemented, and existing voice still explicitly asks for English. Do not
claim the full multilingual acceptance gate or the entire UI-2 phase complete.

### Checks and failures

- Backend Ruff passed; mypy passed for 28 source files; 151 foundation tests passed.
  New tests cover legacy defaults, persistence across login, stale revisions,
  invalid names/timezones/locales/revisions, role/email/user-ID injection, isolation
  and disabled users. Local stores do not prove Atlas persistence.
- Frontend lint/types/build passed. Six Vitest tests passed, including catalog
  key/placeholder parity, timezone formatting and profile-contract validation.
- All 17 Playwright tests passed. New profile tests exercise save/reload/login,
  stale edits, three interface locales, active-request identity and original-result
  continuity, and uninterrupted audio objects through inline locale changes.
- The first new profile browser run had two timeouts: exact `getByLabel` selectors
  failed to identify the language selects despite their accessible combobox names.
  Using `getByRole('combobox', {name, exact:true})` fixed both; the rerun passed.
  Review also fixed Reload to discard stale form state while fetching the latest
  profile. Existing 15 regressions remained green.
- Initial uv checks were blocked by sandbox cache access; permission-enabled runs
  passed. Subsequent CI and live acceptance are recorded below.

### Approved Atlas change and verification

Read-only inspection found custom role `telecomDemoIdentityRuntime` in Atlas project
`67b385a7976edf15ecc62e06`, with one direct database-user assignment scoped to cluster
`OpenAI-SDK` (all 18 project database users were inspected). Application runtime has
FIND, INSERT and CREATE_INDEX on `telecom_identity.users`, originally lacked UPDATE. The
runtime cannot list collection validators; a separate existing administrative
read confirmed collection options `{}`. No validator migration is required.

Snapshots: [original role](../../compatibility/ui2a-identity-role-before.json) and
[proposed role](../../compatibility/ui2a-identity-role-proposal.json). The only delta
is UPDATE on `telecom_identity.users`. Preserve every current privilege and inherited
role. Re-read before applying and stop on drift. A database-user assignment count
is not proof that no other process uses the same credential.

Approved command, executed successfully after confirming no role drift:

```sh
atlas customDbRoles update telecomDemoIdentityRuntime \
  --projectId 67b385a7976edf15ecc62e06 \
  --append --privilege UPDATE@telecom_identity.users
```

MongoDB collection UPDATE is not field-level authorization: it also permits updating
other fields in users. The backend's strict profile allowlist and session-derived
identity enforce own-profile writes. This permission must not be extended to other
collections, databases or memory clusters. Rollback removes only the newly added
resource from UPDATE after re-reading the role; never overwrite unrelated changes.

The requester explicitly approved the mutation and one temporary synthetic account
smoke test. The role change was applied and a fresh read verified exactly one added
grant, with all other and inherited privileges preserved:
[role evidence](../../compatibility/ui2a-identity-role-evidence.json).

The real FastAPI profile/login routes were exercised through TestClient with the
runtime MongoDB identity and one new synthetic account. This was not a mock database.
Checks passed for legacy defaults, HTTP 200 save/read, actual MongoDB persistence,
HTTP 409 stale revisions, HTTP 400 invalid/privileged fields, logout and new-login
continuity. Administrative credentials were used only for scoped cleanup, not for
profile writes. [Live evidence](../../compatibility/ui2a-profile-live-evidence.json)
confirms the account was removed and zero test sessions/login-attempt records remain.
No real user profile, Engine memory, provider configuration or other collection role
was changed. This is an in-process HTTP + real Atlas proof, not deployment to the
already-running demo server.

Initial commit `408c3c0` passed repository/application CI in push run `41323306419`
and PR run `41323339507`; no remote checks failed. This evidence update requires a
fresh CI gate before merge. UI-2a acceptance is complete; the entire UI-2 and full
multilingual response/voice acceptance remain open for their subsequent phases.


## UI-2b profile photo — 2026-11-01

UI-2a final commit `e0e2992` passed repository/application jobs in runs `41324612654`
and `41324617481`, then PR #7 merged as `c62b99a`. UI-2b branches from that main.

Added JPEG/PNG-only normalization with Pillow **13.0.0**, pinned in pyproject and
uv.lock. PyPI metadata confirmed Python >=3.11 and CPython 3.15 wheels for macOS/Linux;
the Python 3.15.2 local install and `uv pip check` passed. Official
[Pillow Image documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html)
was inspected for open/verify/thumbnail and decompression-bomb handling.

The backend enforces a 2 MiB binary upload, 4096 pixels per side and 4 million decoded
pixels before full loading. It verifies format/MIME, rejects animation and malformed
content, applies EXIF orientation, copies pixels into a fresh JPEG, strips metadata
and bounds the thumbnail to 256px and 128 KiB. Only the normalized bytes are stored
under `profile.avatar`; original uploads are not persisted. Existing profile updates
preserve that independent field. A shared profile revision prevents lost updates.

GET `/api/profile/avatar` returns only the current authenticated user's JPEG with
no-store/nosniff, or 404 if absent. POST on that path adds/replaces; POST
`/api/profile/avatar/remove` removes through an optimistic UPDATE, without a new
collection or extra Atlas privilege. An explicit 2,797,000-byte JSON envelope applies
only to the avatar upload path; other limits are unchanged. No remote URL or SVG
input is accepted. Profile/menu show the photo or escaped initials. All new controls
and errors have three-locale catalog entries.

### Evidence and limitations

- Ruff passed after correcting eight E501 line-length findings; mypy passed for
  29 source files. All **163** foundation tests passed, including normalization,
  EXIF/metadata removal, oversized dimensions, format/MIME mismatch, animation,
  malformed/base64/truncated input, scoped read/write/remove, stale revisions and
  preservation of profile fields. No backend behavior assertion failed.
- Frontend lint, types/build, six unit tests and **18 browser tests** passed.
  Browser coverage includes the complete photo lifecycle with the real normalization
  endpoint and an in-memory identity store, plus all previous regressions.
- Visual review at 390px caught a hint overlapping Reload profile; the profile-only
  hint margin was corrected. The browser suite was rerun to regenerate evidence.
- All 59 installed packages passed `uv pip check`. No new Atlas mutation, live photo
  write or provider call was performed in UI-2b. The prior UI-2a grant and Atlas
  persistence proof remain valid historical evidence, not a claimed live avatar test.
- No photo/user listing endpoint or broader role was added. Do not present this
  phase as password-change or multilingual speech completion. Required CI remains
  the final publication gate; rollback can revert UI/API while retaining harmless
  normalized profile fields until a separately approved deletion is requested.


## UI-2c password change — 2026-11-01

UI-2b commit `ce3c01a` passed repository/application CI in runs `41326753953` and
`41326781298`; PR #8 merged as `9f466e5`. UI-2c branches from that integrated main.

POST `/api/profile/password` requires an authenticated session, current password,
8–128-character new password and matching confirmation. Extra identity/role fields
are rejected. The password hash and credential version change atomically through
an expected-hash update on the same user. Every session authorization rereads the
user credential version; legacy users/sessions default to version 0. Thus all old
sessions become unusable immediately without waiting for deletion or TTL.

Login captures the version from the same verified credential snapshot and rechecks
the newly inserted session. A login racing a password change cannot acquire the new
version using the old password. Password attempts are capped at five per account
per 15-minute window, shared across sessions. Existing PBKDF2 parameters, two roles,
user identity and Engine approval ownership remain unchanged.

The three-language form uses transient form fields, clears them after every result,
never stores passwords in browser storage and requires fresh login after success.
Uncertain requests are not retried or presented as successful. No forgotten-password
email or admin reset flow is introduced. No new role or Atlas write was performed.

### Validation and deployment boundary

- Ruff and mypy (29 source files) passed. Initial import-order and line-length lint
  findings were corrected; no behavioral test failed.
- **174 foundation tests** passed, including all-old-session invalidation, current
  password/confirmation/policy failures, field injection, account-scoped throttling,
  a racing login, competing password updates and user isolation.
- **15 identity/admission tests** passed, including revocation before Engine resume.
- Frontend lint/types/build and **6 unit tests** passed; **19 browser tests** passed.
  The password browser test covers failure-field clearing, successful sign-out,
  rejection of the stale cookie and new-password login. Its isolated synthetic
  fixture session avoids weakening/exhausting the real peer login limiter.
- No real user password or live Atlas credential/session was changed. This validates
  application behavior with local fixtures; it is not a deployed password rollover.
- Deployment must restart/upgrade **every identity-serving process** before enabling
  password changes. Mixed old/new processes are unsafe because old code ignores the
  credential version. Roll back UI/forms independently, but retain version checks;
  reverting to pre-version authentication after a password change could revive old
  sessions. Any physical live-session cleanup requires its own approved scope.
- Required remote CI remains the publication gate. Provider-language, settings,
  Tokenomics, memory migration and final integrated acceptance remain separate work.


UI-2c source commit `8ccc58b` passed both repository/application jobs in CI runs
`41328839804` and `41328845361`. PR #9 merged as `16681b9`; no remote check failed.
This is integration evidence, not deployment to existing identity-serving processes.
The next bounded work is LANG-0; see the [multilingual rollout](../runbooks/MULTILINGUAL.md).


LANG-3 scope exception: the requester explicitly accepted the real three-language
voice demo and regression evidence in place of the complete nine-case matrix.
[I18N-001](I18N-001-MULTILINGUAL.md) records the decision and limitations. This does
not waive UI-3, Tokenomics, memory-migration or UI-4 gates.
