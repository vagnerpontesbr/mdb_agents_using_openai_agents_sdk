# ADR-0006: Separate RAG faithfulness from time-valid business correctness

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

A benchmark built from the same stale corpus can reward obsolete answers.

## Decision

Version independent SME-approved truth with effective time/product/firmware scope. Report retrieval, faithfulness, citations, governance, and business outcomes separately.

## Alternatives considered

One aggregate RAG score; answer accuracy evaluated solely against generated corpus-derived labels.

## Consequences and tradeoffs

More annotation and reporting effort; illustrative fixture scores are never presented as measurements.

## Validation before acceptance

Run stale-gold negative control, governed abstention, and current-replacement cases; retain actual grader outputs and business outcomes.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
