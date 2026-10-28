# ADR-0008: Reuse the agent workflow across chat and browser voice

- Status: Proposed
- Date: 2026-10-28
- Owner: Architecture owner, to be assigned
- Evidence: [implementation plan](../../initial_plan.md) and its linked research; [best practices](../BEST_PRACTICES.md)

## Context

Voice must share business policy, memory, and tools without duplicating orchestration.

## Decision

Start with chained STT to the same Python supervisor to TTS. Normalize audio, commit final transcripts once, and validate answers before speech where required.

## Alternatives considered

Independent voice business logic; claim full-duplex behavior without validating Realtime.

## Consequences and tradeoffs

Turn-based voice has latency and interruption limits; telephony remains an explicit integration extension.

## Validation before acceptance

Complete a spoken request, continue via chat, test cancellation/disconnect/noise, and confirm effects once.

## Revisit trigger

Revisit when a provider contract changes, a required capability fails validation, or measured quality, load, security, or cost invalidates the assumption. Record evidence and a superseding decision rather than silently rewriting accepted history.
