# ADR-0023: Limit demo voice acceptance to a quiet environment

- Status: Selected by explicit user instruction; bounded microphone/listening proof passed
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0008](0008-voice-channel.md)

## Context

The user completed a real microphone, Engine voice/chat and listening test.
A generated fixture with 10 dB additive noise was rejected before Engine dispatch.
That demonstrates safe rejection, not reliable recognition in noise. The user
explicitly accepted limiting the voice demo to a quiet environment.

## Decision

Accept voice for the validated English synthetic phrase in a quiet environment.
When speech is not recognized, show an actionable message and permit a bounded
manual retry before Engine work begins. Reliable noisy-environment recognition
is outside current demo acceptance and no longer a Phase 0 gate.

Keep validation, requester/action controls and Engine ownership unchanged. Do not
weaken input validation, fabricate a transcript, or silently retry accepted work.
The microphone probe permits at most three voice submissions per process.

## Alternatives considered

Continue noise robustness work before demo acceptance; or accept the tested quiet
environment and preserve the observed noise limitation. The user selected the
latter. Removing the synthetic-input guard was not selected.

## Consequences and tradeoffs

Use a quiet setting and the displayed English phrase for the demo. Speech may
still need repetition. This decision does not establish an acoustic benchmark,
general speech accuracy, multilingual support, remote cancellation or hosted
service-outage recovery. The hosted dependency-failure gate remains separate.

## Validation

[Microphone and listening evidence](../tasks/COMP-004-VOICE.md#real-microphone-and-user-listening-pass)
records two completed Engine executions and explicit user listening confirmation.
[Fault evidence](../tasks/COMP-003-FAULTS.md#http-delivery-and-voice-dependency-faults-bounded-follow-up)
distinguishes safe noisy-input rejection, provider denial and local HTTP tests.

## Revisit trigger

Revisit when noisy or multilingual operation becomes a requirement, using a
representative audio evaluation set and explicit accuracy criteria.
