# ADR-0031: Dedicated mymemory destination for Engine-managed memory

- Status: Dev-only fresh destination authorized on 2026-11-02; live cutover passed; publication tracked in MEM-002
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0017](0017-two-cluster-memory-boundary.md)

## Context

At proposal time, Engine memory used ClusterDemoTelco and is project-scoped. The requester
wants to move this memory to mymemory and change the DemoTelco project later.
Application data must remain separate and prior memory ownership must be preserved.

## Decision

Use mymemory as the dedicated destination and retain OpenAI-SDK for application
data. The accepted dev cutover uses mymemory for memory and the managed project store;
ClusterDemoTelco is retained as the historical source.
Engine remains the managed-memory owner. Local `MYMEMORY_MONGODB_URI` is a private
administrative input, not an application connection or automatic Engine override.

The authoritative phased plan is [MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md).
The requester confirmed both workspaces may move together and explicitly accepted
memory loss in preview/development on 2026-11-02. For this dev-only cutover, initialize
Engine-managed memory on mymemory without copying old records; retain the source.
The requester subsequently authorized copying dependencies: the mdb_store database
was copied and its scoped roles added, after a memory-only role caused orchestration
readiness failure. Historical memory transfer, quiescent snapshot and zero-loss reverse reconciliation are not
acceptance requirements for this change. They remain future product-manager review,
not supported production migration claims. Verify the actual destination, scoped
identity, native write/read and user isolation before declaring success.

## Alternatives considered

Keeping ClusterDemoTelco does not meet the requested destination. Moving application
data as well breaks the requested separation. An application-owned memory copier or
dual writer breaks Engine ownership. A new Engine project may isolate consumers but
requires a separate concrete proposal; it is not implicitly authorized by this plan.

## Consequences and tradeoffs

Data restore, index readiness, runtime attachment and semantic recall are independent
checks. Retain a consistency point, bounded change window and rollback accounting for
new target writes. Preserve historical observations; do not relabel them as mymemory
evidence. The exact new database user and project-secret change were proposed and approved
with "continuar". The runtime identity is restricted to the project memory database
and mymemory cluster. Existing administrative credentials and source data are retained.

## Validation

For the dev override require target identity/role readback, native canary write/read,
cross-user denial, application connectivity and redaction evidence. Do not claim
historical two-user continuity or an archival restore rehearsal. No new 30-day expurgo, pricing or production
capacity proof is needed. All migration acceptance checks remain unrun.

## Revisit trigger

Unsupported managed-data migration, shared project consumers that cannot move,
incompatible target capabilities, or a later DemoTelco project migration.
