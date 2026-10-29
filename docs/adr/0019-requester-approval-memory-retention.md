# ADR-0019: Requester approval and thirty-day memory retention

- Status: Selected by user; enforcement compatibility pending
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0017](0017-two-cluster-memory-boundary.md), [ADR-0018](0018-engine-feature-precedence.md)

## Context

The user selected self-approval by the requester and retention/deletion after 30 days. The approved Engine project also serves another application. Existing review and memory probes establish bounded execution behavior, not independently authenticated requester authorization or lifecycle deletion.

## Decision

The authenticated requester may approve their own exact pending action. No separate reviewer is required. Another user does not gain approval rights by knowing the session, execution or interrupt ID. Backend authorization must bind the authenticated principal to the original requester and current action before accepting a decision through Engine. A caller-supplied user ID is not authentication. Existing action identity, expiry and idempotency checks still apply.

Retain this application's conversations and derived memories for 30 days, then delete them through supported Engine lifecycle mechanisms. The implementation must define and verify the age origin and deletion completion behavior before claiming compliance; promotion or replay must not silently renew source retention. This does not select a 30-day approval timeout: approval expiry is a separate concern, and the existing 60-second timeout is only a synthetic test fixture.

Preserve Engine ownership and the shared-project boundary. Do not add direct MongoDB TTL indexes, a competing memory writer or a deletion job against managed collections. Do not apply project-wide settings to the other application merely to satisfy this requirement. A verified application-scoped lifecycle contract is required; otherwise the integration gate stays blocked.

## Alternatives considered

A separate reviewer and indefinite retention were not selected. Project-wide retention changes, moving the workspace to another project and application-owned memory cleanup are not approved substitutes for the existing architecture.

## Consequences and tradeoffs

Self-approval simplifies the business workflow but still requires a second authenticated identity for the denied-access test. Thirty-day retention requires coverage of source turns, snapshots and derived memory, including asynchronous extraction and later retrieval. Snapshot TTL alone is not proof of complete lifecycle enforcement. Backup, trace and external-provider retention are distinct surfaces, not established by this memory requirement.

## Validation

Track the pinned contract findings and acceptance controls in [COMP-005](../tasks/COMP-005-AUTH-RETENTION.md). Require requester success, different-user denial and spoofed-requester denial. Require before/after expiry controls for synthetic source and derived records, no retrieval or regeneration after deletion, and preservation of unrelated application data. Neither mock tests nor a declared retention field prove remote deletion.

## Revisit trigger

Revisit if Engine cannot scope the lifecycle to this application, cannot expose a trusted requester identity, or if a different approval or retention policy is requested.


## Acceptance adjustment selected by the user

The user subsequently waived application-specific proof of native memory expurgo. Retention remains an Engine-owned thirty-day requirement; physical deletion, cascade coverage and per-type expiry tests are no longer Phase 0 blockers. Earlier validation requirements for those probes are superseded by this explicit instruction. This is acceptance of platform responsibility, not a claim that shared settings were changed or every memory type was empirically validated. Requester authorization and other integration controls remain required.
