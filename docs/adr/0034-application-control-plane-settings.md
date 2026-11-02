# ADR-0034: Application Control Plane settings and request snapshots

- Status: Accepted and implemented; explicitly approved Atlas resource/persistence gate passed
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0030](0030-ui-profiles-control-plane.md)

## Context

The requester permits administrators to edit application limits and retrieval-cache
settings, applying changes to subsequent operations without restarting ongoing work.
Application library retrieval and hosted Engine retrieval have separate runtime owners.

## Decision

Persist one application-owned document in telecom_identity.application_settings on
OpenAI-SDK. Keep the existing restricted identity client. The reviewed role proposal
adds FIND/INSERT/UPDATE for this collection only, leaving existing grants unchanged.
Do not give the runtime validator/index management, deletion or cluster-wide access.

Editable integers are chat_max_chars (100–4000), knowledge_query_max_chars (100–2000)
and library_cache_max_age_seconds (1–900). Immutable code ceilings remain authoritative.
This cache control applies to library search through the application, not hosted
Engine retrieval. Models, secrets, feature toggles, Engine policy and memory stay
read-only. Configuration presence is not a health check.

Each request reads and captures immutable values before admission or retrieval.
Store failures in enabled deployments fail closed; they do not silently use defaults.
An absent settings document uses labeled code defaults until the first explicit save.
Disabled deployments retain existing defaults and show read-only settings.

Each save compares the expected revision and atomically updates values, revision
and a bounded list of the last 20 changes (actor ID, timestamp, before/after values).
This is an operational change history, not an indefinite compliance audit. Reapplying
old values is a new revision; no reset of revision or unconditional overwrite.

## Alternatives considered

Process-local mutable state would diverge between backends and disappear on restart.
Editing arbitrary environment values would expose secrets and include settings that
cannot safely change during execution. Updating hosted Engine settings from this
UI would cross its ownership boundary. An unbounded audit array would grow indefinitely.

## Consequences and tradeoffs

A new collection and narrowly scoped role extension require explicit Atlas approval.
Reading current settings adds a bounded application-database read at admission.
In-flight executions retain admitted arguments; save does not mutate their identity,
approval digest, text or stored locale. Shorter cache age rejects stale entries without
deleting shared cache data or changing its indexes.

## Validation

Role/unauthenticated denial, pagination, exact public projection, strict values,
stale-revision rejection, no fallback on enabled-store failure, admitted-versus-next
request behavior and per-request cache age are tested locally. Browser tests cover
reload persistence with an in-memory fixture, conflict/uncertain-write handling and
multilingual layouts. Live persistence and role/schema readback remain separate gates.

## Revisit trigger

New fields, hosted cache control, multi-application scope, indefinite audit retention,
configuration subscriptions or changes to Engine ownership require a new review.


The requester approved the exact resource proposal. Strict validator/role readback and real HTTP restart, stale-revision and normal-user-denial acceptance passed; settings were restored at revision 3. See [UI-3 evidence](../runbooks/UI_3_CONTROL_PLANE.md).
