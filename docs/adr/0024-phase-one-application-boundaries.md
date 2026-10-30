# ADR-0024: Deliver the application foundation through the existing identity boundary

- Status: Implemented and locally validated for Phase 1; remote publication pending
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0002](0002-service-boundaries.md), [ADR-0009](0009-deterministic-responses.md), [ADR-0020](0020-demo-email-password-auth.md)

## Context

Phase 0 established bounded provider integration and a working identity service.
Phase 1 needs an installable backend, React application, typed contracts and
repeatable checks. Building empty knowledge/worker services or a second identity
store would add unvalidated boundaries without delivering a user behavior.

## Decision

Deliver an authenticated account journey: sign in, restore the browser session,
administrator registration and logout. Use FastAPI as same-origin ingress and
serve the built React/TypeScript application from its loopback origin. Reuse
`compatibility.demo_auth` implementation and its existing collections, hashes,
sessions and role checks through a typed facade; no account migration or password
reset is required. The application package includes those source modules without
copying their implementation. Its entrypoints do not import the legacy Engine
transport or require Engine/OpenAI dependencies.

Process and write ownership:

| Process / command | Work and write ownership |
| --- | --- |
| `telecom-api` | HTTP identity operations on `telecom_identity.users`, `sessions`, `login_attempts`; no index creation at startup |
| `telecom-admin migrate --apply` | Idempotent v1 identity indexes only, using separately injected configuration when a migration identity is available |
| `telecom-admin bootstrap --apply` | Insert-only initial administrator with hidden password input; never an HTTP route |
| Existing Engine entrypoint | Separately deployed bounded Phase 0 runtime; remains the owner of execution, memory, approvals/replay and primary traces |
| Future knowledge service and ingestion worker | Separate process/write boundaries; implementation deferred to Phase 4; OCR never enters the identity server |

Keep financial/technical/sales specialists together in the future Engine runtime.
This phase does not register placeholder tools or create their databases. The
existing private CLI identity exception remains scoped to the Phase 0 demo;
Phase 1 identity startup never calls Engine or a model provider.

Define strict Pydantic interpretation/outcome contracts without caller-selected
identity or execution authority. Add a versioned invoice template renderer taking
validated business facts, with integer monetary formatting. The full pipeline
that supplies authorized facts and prevents later model rewriting belongs to
Phase 2. A schema-valid model response is not authorization or factual proof.

The identity namespace remains the approved `telecom_identity` on OpenAI-SDK.
Configuration rejects a different SRV host, database path, insecure TLS flags or
public origin. Only `user` and `admin` roles exist. There is no broad fallback URI,
new memory writer, application review database or transcript store.

## Alternatives considered

- Rewrite identity in the new server: rejected because it duplicates validated
  password/session policy and risks changing the demo's existing users.
- Scaffold every planned service now: deferred until each delivers its own
  bounded behavior and validated dependencies.
- Enable cross-origin browser authentication: unnecessary for the local demo;
  same-origin cookies and strict Origin/Host checks simplify the boundary.

## Consequences and tradeoffs

The packaged facade still depends on the legacy identity source location. Root
strict type checks cover the new boundary; the legacy implementation retains its
separate behavioral suite. Its future relocation must preserve imports/data and
be independently tested. The package is not an Engine deployment artifact.

Use one MongoClient per HTTP process, eight admitted requests and a pool ceiling
of sixteen per server (no prewarming). The existing short identity workload gets
a 15-second per-operation budget and a two-second pool wait ceiling. These are
bounded local-demo choices, not measured production sizing. Monitor pool checkout
failures, connection creation and total connections before scaling replicas.

HTTP is loopback-only, so its HttpOnly/SameSite=Strict session cookie does not use
Secure. Public deployment requires a separate HTTPS/identity decision. No browser
storage contains tokens or passwords. The new frontend has no chat/voice feature
until the later journey phase.

## Validation

See [FND-003](../tasks/FND-003-FOUNDATION.md) for executed checks, versions and
limitations. Acceptance covers clean frozen installs, wheel/sdist, backend tests,
lint/types, React build, real-browser account flow against synthetic storage,
bounded admission and exact template assertions. A real authenticated Atlas read
is separate from browser tests and does not claim new hosted integration.

## Revisit trigger

Revisit when implementing Phase 2/4 boundaries, public deployment, new identity
tenancy, measured pool contention or a changed provider/runtime contract. Do not
expand permissions, create empty services or duplicate Engine ownership merely
to satisfy the original proposed directory tree.
