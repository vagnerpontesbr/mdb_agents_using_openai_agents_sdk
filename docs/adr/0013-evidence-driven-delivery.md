# ADR-0013: Deliver bounded tasks with explicit acceptance evidence

- Status: Selected for repository foundation; remote/runtime verification pending
- Owner: Repository maintainer
- Evidence: [official Codex AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [contribution workflow](../../CONTRIBUTING.md)

## Context

The framework spans providers and domains; broad phases alone can hide untested assumptions and generate speculative scaffolding.

## Decision

Use a dependency-ordered backlog and small vertical tasks with scope, acceptance, validation, and evidence. Separate design, local completion, real integration proof, and remote publication status. Review the existing remote before merging local work.

## Alternatives considered

Implement all service scaffolding at once; mark provider integration complete using mocks; let long-lived chat history serve as the task tracker.

## Consequences and tradeoffs

Requires concise task maintenance but makes progress reviewable. Compatibility failures can block dependent tasks without stopping independent work. No extra agents or custom skills are mandatory.

## Validation

Check task handoffs contain actual commands/results and version evidence; accept provider tasks only after live contract tests; verify remote commit/PR status independently.

## Revisit trigger

Revisit if repository size, verified tooling, provider contracts, or the team's review workflow materially changes. Keep commands and completion claims aligned with evidence.
