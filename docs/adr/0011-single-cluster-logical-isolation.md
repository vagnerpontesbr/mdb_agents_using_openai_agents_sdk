# ADR-0011: Use one Atlas cluster with service-owned databases and collections

- Status: Selected by user; implementation verification pending
- Owner: Architecture owner, to be assigned
- Specification: [data architecture](../DATA_ARCHITECTURE.md)

## Context

The user requires one cluster with service/domain ownership and Twelve-Factor application practices.

## Decision

Use one Atlas cluster with environment/domain databases, service-owned collections, and least-privilege identities. Keep eval/load namespaces isolated on that cluster. Preserve managed Engine/Auto Embedding namespaces and verify same-cluster compatibility. Apply Twelve-Factor to config, backing services, stateless processes, releases, logs, and admin jobs.

## Alternatives considered

One broad shared credential; databases/collections per agent/customer; separate Atlas clusters. These weaken ownership, cause unjustified namespace growth, or conflict with the selected scope.

## Consequences and tradeoffs

Logical access boundaries share compute, storage, backup administration, and failures. Tenant filtering remains an application responsibility. Tests can affect demos, requiring budgets and scheduled load windows.

## Validation before implementation acceptance

Verify permitted/denied operations per identity, no demo-to-eval access, CRUD/search/cache tenant isolation, migrations, pool totals, and Engine attachment to the same cluster.

## Revisit trigger

Revisit when measured capacity, physical isolation, recovery, residency, or unavailable provider capabilities invalidate assumptions. Record evidence and an explicit scope decision rather than silently adding products or clusters.
