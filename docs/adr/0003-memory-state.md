# ADR-0003: Separate conversation, durable memory, and execution state

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

Transcripts do not capture paused execution, and eventual memory extraction cannot guarantee next-turn history.

## Decision

Use Engine memory as authoritative memory provider, explicit SDK session adaptation, and versioned run/approval snapshots. Mem0 is a conceptual reference, not a second manager.

## Alternatives considered

Persist everything as chat messages; run Engine and Mem0 as competing memory writers.

## Consequences and tradeoffs

Requires explicit mapping, concurrency control, retention, and deletion of derivatives.

## Validation before acceptance

Test immediate continuity, delayed extraction, concurrent turns, approval resume, and deletion across tenants.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
