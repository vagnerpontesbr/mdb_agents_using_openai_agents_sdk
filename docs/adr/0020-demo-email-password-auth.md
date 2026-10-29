# ADR-0020: Demo email/password authentication and administrator registration

- Status: Selected by user; local identity/UI, Atlas persistence and bounded Engine admission validated
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0019](0019-requester-approval-memory-retention.md)

## Context

The user selected application-owned email/password login for this demonstration asset. An external identity provider is not required. There are exactly two roles: `user` and `admin`.

## Decision

Only authenticated administrators may register users and select either supported role. There is no public self-registration. The initial administrator is `admin@mongodb.com`; its user-supplied initial password is injected privately at bootstrap, not reproduced in source, examples or this record. Bootstrap inserts once and never resets an existing account.

Store users and salted password hashes in the application cluster's `telecom_identity.users`, separate from Engine-managed memory. Normalize email for unique lookup; use a stable opaque user ID for authorization. The bounded module uses PBKDF2-HMAC-SHA256 with 600,000 iterations and independent 128-bit salts. No plaintext password, password hash or login token is returned in the public principal.

Administrator privileges cover user administration. They do not grant approval of other users' pending actions: the authenticated original requester remains the approver under ADR-0019. Backend code must enforce this before forwarding a decision to Engine. Application roles are not Engine project/database roles.

## Alternatives considered

External OIDC was not selected for the demo. Public registration and implicit administrator override of requester approval were not requested. Hardcoded bootstrap passwords and plaintext password storage are excluded.

## Consequences and tradeoffs

The app must implement login sessions, logout, bounded login attempts and browser cookie/CSRF controls when its HTTP layer is added. The later loopback compatibility UI now implements those controls with opaque one-hour sessions and a fixed eight-attempts-per-peer/minute throttle; it is not a public deployment. Password recovery and external email verification have not been requested.

The user decision resolves the missing application authentication choice. Engine credential delegation, prevention of direct resume bypass, trusted original-requester metadata and native admission remain independent compatibility gates; local account creation alone does not prove them. The later bounded demo bridge validates pre-resume admission using two app accounts behind a private human CLI credential; deployable least-privilege/service-account behavior remains unproved.

## Validation

[COMP-005 demo authentication](../tasks/COMP-005-DEMO-AUTH.md) tracks salted storage, admin-only creation, duplicate/bootstrap preservation, invalid/disabled identities and requester-only authorization with independent passwords. Distinguish in-memory contract tests from real MongoDB persistence and hosted Engine enforcement.

## Revisit trigger

Revisit when the asset requires external identity federation, production deployment, password recovery or additional administrative powers.
