# ADR-0015: Preserve Python 3.15 and use the official Voyage HTTP API

- Status: Selected by the user; live integration verification pending
- Owner: Repository maintainer
- Evidence: [Phase 0](../compatibility/PHASE_0.md), [contextual embeddings](https://docs.voyageai.com/docs/contextualized-chunk-embeddings), [reranking](https://docs.voyageai.com/docs/reranker)

## Context

Captured voyageai 0.5.0 package metadata excludes Python 3.15. The user explicitly selected Python 3.15 with official Voyage HTTP calls instead of downgrading Python or changing models.

## Decision

Keep Python 3.15 (current validation target 3.15.2) and uv dependency management. Exclude the incompatible voyageai Python SDK from the candidate application dependencies. Use the official Voyage REST API behind an application adapter wherever direct calls are needed. The user confirmed an Atlas-issued model API key: configure `VOYAGE_BASE_URL=https://ai.mongodb.com/v1`. Voyage-platform keys use `https://api.voyageai.com/v1`; geography-scoped Atlas keys require the matching documented host. Never silently send a key to arbitrary or fallback hosts.

Preserve voyage-context-4 with provider auto-chunking for contextual knowledge, voyage-4 and voyage-4-lite for general embeddings, and rerank-3 for reranking (rerank-3-lite remains the planned economy option). MongoDB Auto Embedding remains preferred for supported workflows; this decision changes only the transport for direct Voyage calls.

The Phase 0 adapter is a bounded synchronous diagnostic for contextual embeddings and reranking, not the production ingestion client. Production transport must support concurrency limits, cancellation, bounded retries for transient failures, deadlines, usage accounting, and secret-safe telemetry. Validate response dimensions, chunk provenance, document indices, and finite vector values at the boundary.

## Alternatives considered

Downgrade the whole project; isolate the Voyage SDK in an older-Python worker; wait for a compatible SDK release. HTTP avoids adding a service solely to work around this SDK constraint.

## Consequences and tradeoffs

Preserves the requested runtime and models but makes the asset responsible for HTTP contract validation and resilience. Removing the SDK constraint does not prove compatibility of Docling, Engine memory, or other transitive packages. Engine-managed memory may have its own dependency requirements; validate those separately without replacing Engine memory.

## Validation

Run contract tests on Python 3.15.2, resolve/install the complete graph with uv, and execute bounded real contextual document/query and rerank probes. Add general embedding and production transport tests when those paths are implemented. Test doubles establish adapter behavior only, not provider capability.

## Revisit trigger

Review when an official Python SDK supports the target runtime, API contracts change, or measured HTTP maintenance cost justifies switching. Preserve model and retrieval semantics during any migration.
