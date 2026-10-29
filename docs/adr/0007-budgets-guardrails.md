# ADR-0007: Enforce budgets and authorization outside model prompts

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

Agent fan-out, retries, voice, and background memory/ingestion can amplify costs and side effects.

## Decision

Apply backend tool authorization, bound approvals, idempotency, per-tenant token/time/cost quotas, provider concurrency limits, and a single retry owner. Cache cannot bypass actions or governance.

## Alternatives considered

Prompt-only controls; unlimited retries; optimize solely for token price.

## Consequences and tradeoffs

Admission control and escalation may reduce completion under overload; cost accounting needs dated rates and full component attribution.

## Validation before acceptance

Test budget exhaustion, duplicate requests, stale approvals, provider throttling, output release, and cost per successful outcome.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
