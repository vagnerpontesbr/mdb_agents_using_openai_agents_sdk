# ADR-0030: Profile navigation and application Control Plane

- Status: Accepted for phased implementation; runtime changes not yet implemented
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0020](0020-demo-email-password-auth.md), [ADR-0018](0018-engine-feature-precedence.md)

## Context

The current page combines identity, registration, support and knowledge. The user
requested profile menus and an application Control Plane inspired by `gensdd-main`,
with a dedicated branch and phased quality gates. The reference includes platform
configuration and secret management that cannot be transferred without changing
this demo's ownership boundaries.

## Decision

The UI-0 design and baseline gate is accepted with the requester decisions below.

Use a responsive workspace shell, header profile menu and admin-only Control Plane.
Preserve exactly `user` and `admin`, session-derived identity, owner-bound document
publication and original-requester approval. A profile menu cannot change privileges.

The requester confirmed own name/timezone/language/photo/password features under
[ADR-0032](0032-multilingual-profile.md). Retain bounded user listing and
existing admin account creation and editable application configuration, as confirmed
by the requester. Integration health is observational. Only application limits and retrieval-cache settings are editable. Feature toggles
remain read-only. Save/Apply affects subsequent operations, preserving in-flight
configuration snapshots; no restart/deploy button is included. UI-001 owns detailed gates.
Use allowlisted response contracts; never serialize environment settings or secrets.
Configured capabilities and verified service health are different states.

Use fixed hash navigation compatible with the existing static server initially.
Keep active journey state above routed views and make recording/playback transitions
explicit. Do not add a second Engine memory, policy, approval or trace owner.

The complete scope, provisional choices, phased implementation and acceptance gates
are authoritative in [UI-001](../tasks/UI-001-PROFILES-CONTROL-PLANE.md).

## Alternatives considered

- Copy the entire reference Control Plane: brings unrelated roles, credentials,
  runtime configuration ownership and domain features into this demo.
- Keep adding sections to the existing page: avoids navigation work but leaves
  account administration mixed with the support journey.
- Add a router library immediately: possible later, but not required for a fixed
  set of routes; a dependency needs a concrete benefit and lock/test validation.

## Consequences and tradeoffs

Profile persistence and user listing require real backend work and negative tests.
Navigation must preserve interrupted-run recovery while cleaning up local audio.
Hash URLs are less conventional than path routes but avoid new server fallback
behavior. Configuration editing is restricted to application limits and cache, applied to
subsequent operations without restarting active executions. Photo, password
change and three-language support were explicitly added by the requester in ADR-0032.

## Validation

Require UI-001 gates for navigation, user/admin isolation, own-profile persistence,
typed admin data, no secret exposure, accessibility, and existing journey/knowledge
regressions. No implementation or live acceptance is claimed by this ADR.

## Revisit trigger

Revisit if the requester expands the editable configuration catalog, profile fields,
additional roles, public deployment, or a supported Engine administration surface.
