# ADR-0022: Retain the private Engine CLI identity for the local demo

- Status: Selected by explicit user instruction; existing bounded path validated
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0017](0017-two-cluster-memory-boundary.md) and [ADR-0020](0020-demo-email-password-auth.md)

## Context

The existing loopback demo authenticates users independently with email/password.
Its backend uses the operator's private Engine CLI login to delegate each opaque
app user ID. The documented service-account path cannot yet delegate per-user
identity and requires broad owner permissions to invoke. The user explicitly
accepted retaining the existing CLI login for this demo.

## Decision

Keep the existing operator Engine CLI credential private in the loopback backend.
Accept its broad Engine permissions and operator-managed login/token refresh for
this demo only. A least-privilege unattended Engine runtime identity is no longer
a Phase 0 demo gate. Do not create a replacement service account or merge app
users into one memory identity.

App users continue to log in with email/password and never receive the Engine
credential. The backend still authenticates the original requester, validates the
exact pending native action, and rejects other requesters before resume. App
administrators gain no permission to approve another user's action. Direct
privileged Engine operators remain outside this application admission boundary.

This exception applies only to the Engine caller. Minimum MongoDB application
database permissions, domain authorization, managed-memory ownership and the
two-cluster boundary remain required. It does not authorize public hosting or
broader distribution of the operator credential.

## Alternatives considered

Wait for a supported narrowly privileged delegating Engine credential; or create
a service account that cannot preserve the tested per-user identity. The user
selected retaining the tested private CLI path for the local demo.

## Consequences and tradeoffs

The demo depends on an operator login and periodic token renewal. Compromise of
the backend could expose the operator's broader Engine access. This is an explicit
demo exception, not a least-privilege or unattended-deployment proof. No secrets
are copied into versioned files, browser responses or documentation.

## Validation

[COMP-005](../tasks/COMP-005-DEMO-AUTH.md#authenticated-native-engine-approval-passes)
records the existing real app requester, denied-other-user and stale-action
controls. This decision changes documentation only; no credential, role,
deployment or shared Engine configuration changed.

## Revisit trigger

Revisit before public or unattended deployment, when operator credentials change,
or when Engine supports a narrower delegating runtime identity.
