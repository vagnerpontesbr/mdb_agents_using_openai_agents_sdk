# ADR-0010: Use MongoDB for operational data, Search, and Vector Search

- Status: Selected by user; implementation verification pending
- Owner: Architecture owner, to be assigned
- Specification: [data architecture](../DATA_ARCHITECTURE.md)

## Context

The asset needs operational data plus lexical, vector, and hybrid retrieval. Separate data products add synchronization pipelines, security configurations, deployment tooling, and failure handling.

## Decision

Use MongoDB Atlas as the integrated data platform. Query operational documents natively and apply Search/Vector Search to relevant collections, with native same-collection rank fusion. Prefer Auto Embedding where compatible and preserve authoritative reads for mutable business facts.

## Alternatives considered

An operational database plus separate full-text and vector databases. These can suit other requirements but add unnecessary integration surface here.

## Consequences and tradeoffs

Fewer separately operated data products and application replication pipelines; shared identifiers simplify lineage. Search indexes still have lag and resource costs. External AI/parsing services remain, and cost/performance benefits must be measured.

## Validation before implementation acceptance

Demonstrate operational and lexical/vector/hybrid queries, freshness lag, authorization, index readiness, and contention on the intended collections.

## Revisit trigger

Revisit when measured capacity, physical isolation, recovery, residency, or unavailable provider capabilities invalidate assumptions. Record evidence and an explicit scope decision rather than silently adding products or clusters.
