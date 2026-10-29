# ADR-0004: Prefer native Auto Embedding while preserving contextual retrieval

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

MongoDB supports automatic Voyage 4 embeddings, while requested contextual auto-chunking has a documented support gap.

## Decision

Use Auto Embedding for supported cache/catalog paths, direct voyage-context-4 for technical documents/queries, native rank fusion and Voyage rerank. Keep Engine embedding ownership intact.

## Alternatives considered

Manual embeddings everywhere; replace context-4 merely to use Auto Embedding.

## Consequences and tradeoffs

Two embedding paths require explicit model/dimension lineage, readiness checks, and bounded candidate counts. Matryoshka profiles need measured value.

## Validation before acceptance

Probe supported indexes/queries and native fusion; compare dimensions and reranking on held-out current references.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
