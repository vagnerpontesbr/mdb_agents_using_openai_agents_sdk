# COMP-005: Demo identity contract

- Status: Local UI, sessions, Atlas persistence and bounded authenticated Engine review validated; deployment/least-privilege limits remain
- Owner: Repository implementation
- Dependencies: COMP-005, application-cluster identity configuration
- Relevant ADRs: [ADR-0020](../adr/0020-demo-email-password-auth.md), [ADR-0019](../adr/0019-requester-approval-memory-retention.md)

## Scope

Implement the selected email/password identity contract as a bounded Phase 0 module. Do not scaffold the full application or replace native Engine approvals. [Auth](../../compatibility/demo_auth/auth.py) authenticates credentials before user registration or requester checks. [Mongo storage](../../compatibility/demo_auth/mongo.py) uses only the application identity namespace, with normalized email as the atomic unique `_id`.

## Acceptance criteria

Only a valid admin creates users. Both supported roles work; unknown roles fail. Passwords are independently salted and hashed. Invalid or disabled users fail authentication. Duplicate email and repeated bootstrap never overwrite accounts. A requester may pass the local admission check; another user, including an admin, cannot.

## Bootstrap

Inject `APP_MONGODB_URI` and `APP_MONGODB_HOST` for the approved OpenAI-SDK application cluster. Supply the user-selected initial password at the hidden prompt; do not put it in a shell argument or documentation.

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/bootstrap_demo_admin.py --allow-write
```

The [bootstrap command](../../scripts/bootstrap_demo_admin.py) inserts only the initial admin into `telecom_identity.users`. It reuses one PyMongo client with a fifteen-second operation timeout for this short installation step and keeps the default lazy connection pool. It does not change database roles or Engine settings. This privileged installation operation must never be exposed as a public route.

## Validation plan

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync python -m unittest discover -s tests/demo_auth -v
python3 scripts/check_repository.py
```

## Evidence and handoff

All six deterministic identity tests passed on the frozen Python 3.15.2 environment using an explicitly in-memory repository. The repository checker passed (57 Markdown files, 20 ADRs), and `git diff --check` passed. The Mongo adapter and bootstrap have not yet been executed against Atlas, and the initial administrator has not been created remotely. No actual user password appears in the tests. The existing frozen Python 3.15.2 environment supplies PyMongo; no new dependency or interpreter downgrade is introduced.

The app registration/login UI, authenticated session cookies, login throttling and native Engine pre-resume integration remain outstanding. `authorize_requester` expects an original requester ID obtained from trusted action metadata; accepting that value from a browser would bypass the intended authorization. No local test is presented as Engine enforcement.


## Live application identity and UI checkpoint: 2026-10-29

The initial administrator was inserted successfully into `telecom_identity.users` on `openai-sdk.qrmdk.mongodb.net` using the user's selected password through a hidden prompt. Its password is stored only as a salted PBKDF2 hash. The private `.env` now supplies `APP_MONGODB_URI`/`APP_MONGODB_HOST`, reusing the existing application connection without printing it. This credential is the existing diagnostic credential; minimum database permissions are not established by these tests. No Engine namespace, policy, provider or deployment changed.

[SessionAuth](../../compatibility/demo_auth/sessions.py) adds opaque 256-bit login tokens whose SHA-256 digests are persisted in a separate `sessions` collection. Each session expires after one hour; reads check the timestamp even before asynchronous TTL cleanup. Logout deletes that session. Every authenticated request reloads the current user's active flag, ID and role, so cached sessions cannot retain revoked administrator privileges. A separate `login_attempts` collection provides an atomic eight-attempt limit per peer per fixed one-minute window, including nonexistent accounts. Both TTL indexes belong to application authentication data, not managed conversation memory.

The [loopback HTTP server](../../scripts/serve_demo_auth.py) and [English UI](../../scripts/demo_auth.html) implement login, logout, current identity and administrator-only registration. Mutations require the exact local Origin/Host and JSON content type. Cookies are HttpOnly/SameSite=Strict, and responses are not cached. The HTTP server binds only 127.0.0.1; it is a compatibility UI, not the planned production/React application. Public HTTPS deployment requires Secure cookies and its own reviewed server/deployment configuration. At most eight handlers enter application work simultaneously. No app endpoint bootstraps an administrator.

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/serve_demo_auth.py --port 0
```

Open the loopback address printed by the server. Port 0 selects an unused port; the initial default-port attempt encountered an existing listener, which was left untouched.

[Live HTTP/Atlas evidence](../../compatibility/demo-auth-http-evidence.json) passed ten checks: anonymous denial, foreign-origin denial, admin login/cookie flags, admin registration, duplicate-email rejection without role promotion, user registration/escalation denial, hashed Atlas persistence, logout revocation, login throttling, and bootstrap-admin presence. Chrome independently passed admin login/registration, ordinary-user login with no registration form, and logout. Both disposable synthetic test accounts and their sessions were removed afterward; the bootstrap administrator remains.

The reproducible [live diagnostic](../../scripts/check_demo_auth_http.py) prompts for the admin password and creates/removes only its generated synthetic user:

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/check_demo_auth_http.py --allow-live --url http://127.0.0.1:PORT --output artifacts/compatibility/demo-auth-http.json
```

All eleven local identity/session tests pass on frozen Python 3.15.2; browser JavaScript syntax checking passes. The five new session tests cover independent logout, expiry without TTL deletion, role/active revalidation, invalid tokens and the shared peer throttle. These complement the real database/API controls; neither establishes native Engine requester-only approval. The account-registration/login persistence gap is closed for this bounded demo UI. Trusted Engine action ownership, pre-resume enforcement, delegated memory identity and least-privilege credentials remain separate.


## Authenticated native Engine approval passes

The [Engine admission bridge](../../compatibility/demo_auth/engine.py) uses the authenticated application session and re-reads the original requester from `GET /api/v1/projects/{id}/executions/{execution_id}?workspace_id=...`. The live response includes user, org/project/workspace, session, native interrupts and suspension generation. This source is authoritative for the bounded approval check; the browser cannot supply a requester or Engine session ID. The exact displayed projection is hashed and checked again before native resume, and the app session is revalidated after the Engine read. No approval/checkpoint database or second memory writer is introduced.

The server's opt-in `--engine-review` uses the existing operator CLI login privately on the backend. Only that credential invokes Engine; application users have independent email/password sessions and receive no Engine credential. Human CLI delegation preserves each application's opaque user ID in the tested hosted execution. This is **not** evidence that service-account delegation works, nor a least-privilege runtime credential solution. Operators with direct Engine access remain outside the demo application admission boundary.

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/serve_demo_auth.py --port 0 --engine-review
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/check_demo_engine_review.py --allow-live --url http://127.0.0.1:PORT --output artifacts/compatibility/demo-engine-review.json
```

A first metadata read returned 401 from the expired CLI access token. The documented `agentengine auth login --from-refresh-token` flow renewed the same existing session using its refresh token in memory; credentials were never printed or copied to the browser. The subsequent authenticated execution read passed. App user/password authentication was unaffected.

[Real native approval evidence](../../compatibility/demo-auth-engine-evidence.json) passed execution `006266d5-8dbe-4dfd-bc1b-f6283d5c5388`: a regular application user initiated the invoice, a separately logged-in application admin received 403 for reading/approving that user's pending action, a spoofed requester field returned 400, and a changed action digest returned 409. A fresh Engine read returned exactly the same pending projection and generation after all denials. The owner then approved the original execution successfully; repeated approval returned 409. The disposable requester account and its app sessions were removed; Engine-owned synthetic memory remains managed by Engine.

The [reproducible diagnostic](../../scripts/check_demo_engine_review.py) performs these controls through the app HTTP boundary and uses Atlas only for its own generated account cleanup. Four new local admission tests independently verify no resume call on different-user/stale-content/scope/generation/session-revocation failures. All fifteen identity/session/admission tests pass in the frozen runtime and with the standard-library test invocation now included in repository CI. The committed/published CI result remains unverified until the user commits/pushes.

This closes authenticated requester self-approval for the tested local-demo access path, superseding the missing-application-identity blocker. It does not add a global requester policy to Engine itself, prove concurrent review races or every native review entrypoint, solve minimum backend credentials, or establish production HTTPS deployment. Full transcript restoration remains a separate task.

Chrome also completed an additional invoice request and self-approval as the initial administrator, displaying the native pending action and the final synthetic invoice. The browser was logged out after validation; the local demo server remains available at the address delivered to the user. No commit/push or Engine redeployment was performed.
