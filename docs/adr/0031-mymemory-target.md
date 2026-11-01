# ADR-0031: Dedicated mymemory destination for Engine-managed memory

- Status: Target requested by user; migration design planned, not applied
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0017](0017-two-cluster-memory-boundary.md)

## Context

Engine memory currently uses ClusterDemoTelco and is project-scoped. The requester
wants to move this memory to mymemory and change the DemoTelco project later.
Application data must remain separate and prior memory ownership must be preserved.

## Decision

Plan mymemory as the dedicated destination and retain OpenAI-SDK for application
data. Keep ClusterDemoTelco as the active source until migration acceptance.
Engine remains the managed-memory owner. Local `MYMEMORY_MONGODB_URI` is a private
administrative input, not an application connection or automatic Engine override.

The authoritative phased plan is [MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md).
Preserve existing memory by default, prove a supported transfer, and resolve
project-wide impact before cutover. A later DemoTelco change cannot be assumed
independent when workspaces share the Engine project.

## Alternatives considered

Keeping ClusterDemoTelco does not meet the requested destination. Moving application
data as well breaks the requested separation. An application-owned memory copier or
dual writer breaks Engine ownership. A new Engine project may isolate consumers but
requires a separate concrete proposal; it is not implicitly authorized by this plan.

## Consequences and tradeoffs

Data restore, index readiness, runtime attachment and semantic recall are independent
checks. Retain a consistency point, bounded change window and rollback accounting for
new target writes. Preserve historical observations; do not relabel them as mymemory
evidence. No existing cluster, secret, role or deployment changes during planning.

## Validation

Require MM-0–MM-5 positive/negative checks, native two-user continuity, application
regression and redaction evidence. No new 30-day expurgo, pricing or production
capacity proof is needed. All migration acceptance checks remain unrun.

## Revisit trigger

Unsupported managed-data migration, shared project consumers that cannot move,
incompatible target capabilities, or a later DemoTelco project migration.
