# ADR-0005: Govern document validity independently of retrieval relevance

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

A relevant, well-cited obsolete SOP can produce a wrong current action and still pass circular evaluations.

## Decision

Require owner, validity/review dates, provenance, applicability, approval, version lineage, and explainable risk. Enforce hard exclusions before publication and response/cache use.

## Alternatives considered

Trust similarity, citation, or ingestion recency as proof of authority; make risk score the sole gate.

## Consequences and tradeoffs

Lower coverage may require abstention; owners must review content. Search lag requires authoritative checks, and a low score never overrides a hard exclusion.

## Validation before acceptance

Execute expired/superseded/review-boundary/cache-race cases and the isolated 80-risk stale-reference demonstration.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
