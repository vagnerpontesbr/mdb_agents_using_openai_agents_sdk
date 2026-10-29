# ADR-0009: Constrain generation and render critical responses deterministically

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [plan section 15](../../initial_plan.md#15-predictable-responses-and-deterministic-business-behavior), [official SDK output contracts](https://developers.openai.com/api/docs/guides/agents/define-agents), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

## Context

Telecom invoices, prices, approvals, and confirmations need stable, auditable facts and wording. LLM sampling, interpretation, changing context, and source quality prevent a general guarantee of identical generated answers. Structured output does not establish semantic correctness.

## Decision

Use the SDK for typed interpretation and specialist work. Validate extracted parameters and clarify ambiguity. Execute business decisions through versioned backend rules and authoritative tools, then render protected responses using approved templates at the final application boundary. Do not let the supervisor rewrite protected rendered text. Use structured, grounded generation for technical explanations with deterministic source-governance checks. Share business rules and rendered text across chat/voice; identical audio is not required.

## Alternatives considered

- Free-form generation for every response: flexible, but permits variation in protected facts and terms.
- Temperature zero or seed as the determinism strategy: model/API-dependent and not a guarantee.
- Templates for every interaction: consistent wording but overly restrictive for explanatory support.
- Semantic cache as repeatability control: may match different contexts or stale sources; cannot certify correctness.

## Consequences and tradeoffs

Templates and rules need versioning, owner review, localization/formatting control, and maintenance. Interpretation remains probabilistic and can require clarification. Determinism applies only to the stated fixed-input/state boundary. Live data and policies must remain current. Refused, incomplete, or invalid structured responses produce a safe fallback rather than business effects.

## Validation before acceptance

Require exact decisions and rendered text in fixed-input unit tests. Test changed state/clock/policies, ambiguous input, model errors, stale sources, retry/idempotency, and supervisor rewrite prevention. Run repeated model evaluations and report schema, routing, parameter, decision, factual, and wording metrics separately. Verify voice receives the approved text. Repeat critical invariants under load; report actual measurements rather than promising deterministic LLM output.

## Revisit trigger

Revisit when business wording requirements, SDK/model capabilities, template maintenance costs, or measured interpretation quality materially change. Preserve accepted history through a superseding ADR.
