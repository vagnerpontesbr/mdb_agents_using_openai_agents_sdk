# ADR-0028: MIT licensing and automated demo handoff

- Status: Accepted by requester on 2026-10-31; implemented for the bounded demo
- Owner: Telecom demo maintainer

## Context

Phase 6 requires reproducible installation, adaptation and a handoff trial. The
requester selected MIT and accepted the completed isolated automated rehearsal
as sufficient for this demo instead of requiring an independent human trial.

## Decision

Distribute original project code under the root [MIT license](../../LICENSE),
including it in Python packages and hosted source stages. Preserve dependency and
service terms. Accept the automated clean-checkout build/browser/adaptation
rehearsal as the Phase 6 handoff evidence. Do not claim an independent developer
performed it, a fresh hosted deployment occurred, or caches were unused.

## Alternatives considered

A separate human acceptance trial would provide additional usability evidence,
but the requester waived that requirement for this demo. Leaving licensing
undecided would prevent a clear reusable package.

## Consequences and tradeoffs

The asset remains a synthetic reference. The accepted rehearsal does not establish
production operations, capacity or unattended credentials. Phase 8 retains its
separate scalability/resilience acceptance. Git commits and pushes remain manual;
phase completion requires stopping before the next phase unless authorized.

## Validation

[REL-001](../tasks/REL-001-HANDOFF.md) records the isolated setup and exact test
counts. The staging test checks the allowlist and exact license bytes. CI correction
`a4f5c4c` passed in run `41207242615`. No application policy was relaxed.

## Revisit trigger

Revisit when distributing third-party assets under different terms, onboarding an
independent operator, or moving beyond the accepted synthetic demo scope.
