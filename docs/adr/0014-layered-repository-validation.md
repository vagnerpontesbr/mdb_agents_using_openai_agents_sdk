# ADR-0014: Automate repository checks and add validation layers with implementation

- Status: Selected for repository foundation; remote/runtime verification pending
- Owner: Repository maintainer
- Evidence: [official Codex AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [contribution workflow](../../CONTRIBUTING.md)

## Context

Documentation already contains many cross-links and ADRs, while no runnable application dependency graph exists.

## Decision

Provide a standard-library offline repository checker and least-privilege GitHub Actions workflow. Add uv-backed build/lint/type/unit/contract checks when manifests exist. Keep credentialed provider evals and budgeted stress suites separate.

## Alternatives considered

Claim planned commands pass; install an unverified dependency stack merely to check documents; run paid provider calls in every PR.

## Consequences and tradeoffs

Immediate executable feedback without inventing a lockfile or application proof. Bootstrap Python may differ from the target runtime and must be disclosed. Local workflow authoring does not establish remote CI execution.

## Validation

Run the checker on real files plus temporary negative fixtures for broken links and missing ADR sections. Later validate clean frozen builds and actual provider suites. Record CI results only after a real run.

## Revisit trigger

Revisit if repository size, verified tooling, provider contracts, or the team's review workflow materially changes. Keep commands and completion claims aligned with evidence.
