# ADR-0002: Separate workloads at justified service boundaries

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

Interactive chat/voice, retrieval, and CPU-heavy PDF extraction have different scaling and failure characteristics.

## Decision

Use independently runnable ingress, agent runtime, knowledge service, and ingestion workers with versioned contracts. Keep specialists together initially; Engine owns memory.

## Alternatives considered

One process for all workloads; or one microservice per specialist/tool.

## Consequences and tradeoffs

More deployment contracts and observability are needed. Shared MongoDB still creates contention. Avoid cross-service writes; isolate resource pools.

## Validation before acceptance

Stress ingestion and interactive traffic together; verify independent scaling, bounded queues, lease recovery, and tenant correctness.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
