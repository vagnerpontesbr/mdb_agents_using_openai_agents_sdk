# ADR-0032: Full profile and multilingual user experience

- Status: Feature scope confirmed by requester; implementation planned
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0030](0030-ui-profiles-control-plane.md), [ADR-0020](0020-demo-email-password-auth.md)

## Context

The requester selected profile name, timezone, language, photo and password change,
then explicitly required Portuguese (Brazil), English and Spanish for interface,
agent answers and voice. The application currently assumes English in several
response templates and the STT language hint.

## Decision

Support `pt-BR`, `en-US`, `es-ES` across all user-facing channels, with authenticated
profile preference and per-execution locale consistency. Preserve stable identity,
Engine ownership, approval semantics, currencies and UTC business rules. User-visible
localization supersedes English-only UI/output guidance; developer docs and source
identifiers remain English.

[I18N-001](../tasks/I18N-001-MULTILINGUAL.md) owns language contracts and phase gates.
[UI-001](../tasks/UI-001-PROFILES-CONTROL-PLANE.md) owns profile fields, safe photo
handling and authenticated self-service password changes. Roles/email remain read-only
in this profile; password reset for forgotten credentials is outside this request.

## Alternatives considered

UI-only localization fails the requested response/audio scope. Automatic translation
of every final response can alter protected amounts, approvals or procedure steps.
Independent memory per language would fragment identity and conflict with Engine
ownership. Use localized templates and governed content with one identity instead.

## Consequences and tradeoffs

Catalog completeness, deterministic templates, locale transport and actual speech
quality require separate tests. Native voice language support does not prove the
application integration. Safe session invalidation and server-side photo processing
expand UI-2 backend work; split it into reviewable subphases.

## Validation

Require three-language interface and response tests, cross-user negative controls,
protected-template assertions, image validation, password/session revocation tests,
and bounded real voice plus human listening acceptance. No implementation is claimed.

## Revisit trigger

Additional locales, independent output-language controls, new voices/models,
forgotten-password recovery or administrator password-reset privileges.
