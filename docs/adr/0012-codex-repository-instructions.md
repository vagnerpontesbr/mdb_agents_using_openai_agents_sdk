# ADR-0012: Use concise repository instructions as Codex working context

- Status: Selected for repository foundation; remote/runtime verification pending
- Owner: Repository maintainer
- Evidence: [official Codex AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [contribution workflow](../../CONTRIBUTING.md)

## Context

A long plan is useful design context but is not automatically loaded as repository instructions. Repeated policy copies drift.

## Decision

Use root AGENTS.md to define entry points, invariants, actual commands, review rules, and completion reporting. Link detailed specifications; add nested instructions only for real subsystem needs. Keep global developer settings unchanged.

## Alternatives considered

Rely only on conversation history; duplicate the whole plan in instructions; require custom skills for routine work.

## Consequences and tradeoffs

More predictable task context with low duplication. Instructions guide work but do not enforce security or enable GitHub integration. The latest authorized user direction remains authoritative.

## Validation

Verify the instruction file links, documented commands, and applicable instruction discovery in a fresh Codex session when available.

## Revisit trigger

Revisit if repository size, verified tooling, provider contracts, or the team's review workflow materially changes. Keep commands and completion claims aligned with evidence.
