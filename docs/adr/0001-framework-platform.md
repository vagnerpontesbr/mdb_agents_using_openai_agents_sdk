# ADR-0001: Separate agent framework from agent platform

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

The asset requires OpenAI orchestration and MongoDB platform capabilities without assuming identical runtime contracts.

## Decision

Keep OpenAI Agents SDK as the orchestration framework. Integrate Engine memory separately and gate hosted Engine execution on audit/replay compatibility.

## Alternatives considered

Replace orchestration with LangGraph; or embed all platform APIs throughout domain code.

## Consequences and tradeoffs

Adapters and contract tests add effort, but preserve domain portability. A memory integration alone cannot certify hosted execution.

## Validation before acceptance

Prove tool/LLM wrapping, streaming, memory, approvals, and replay in the chosen deployment.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
