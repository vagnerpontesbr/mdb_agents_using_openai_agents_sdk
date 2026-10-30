# ADR-0025: Bounded telecom supervisor and specialist journey

- Status: Implemented; bounded hosted and browser acceptance passed
- Owner: Repository implementation
- Date: 2026-10-29
- Scope: Phase 2 (VERT-001 and VERT-002)

## Context

Phase 1 provides authenticated identity and the React shell. The user authorized
Phase 2 after committing Phase 1. The journey needs three specialists and browser
voice while retaining the ownership rules in [ADR-0018](0018-engine-feature-precedence.md).
A general Responses continuation adapter has not been validated.

## Decision

Use a real OpenAI Agents SDK supervisor with three `Agent.as_tool()` specialists:
financial, technical and sales. Each specialist exposes one typed function tool
and returns after that tool. The supervisor retains orchestration ownership;
backend templates render the tool facts rather than the model's final wording.
The domain supports invoice `demo-1`, a synthetic network check, and eligible
`fiber-500`/`fiber-1000` offers. These are fixtures, not live billing/CRM data.

All hosted inference and business tools use the Engine secure proxies. Each model
call performs fresh inference over a bounded JSON projection of SDK items in the
user data channel. This does not reconstruct hidden reasoning, use provider
conversation IDs, or implement general Responses continuation. Memory remains
Engine-owned semantic/episodic retrieval under [ADR-0021](0021-demo-semantic-episodic-continuity.md).
No application transcript, approval or execution store is added.

A proposed plan change suspends through the existing Engine review activity with
a five-minute deadline. Only the original authenticated requester can submit the
exact displayed action. The backend checks Engine scope and hashes the complete
review plus suspension generation. The intended resume endpoint pins that native
generation; the tested native JSON `human_review` envelope is strictly translated into the
domain decision after Engine activity replay. Unknown contracts fail closed.

Approved changes produce deterministic simulation receipts, with no live charge
or account mutation. The receipt binds the authenticated subject, plan and current
fixture price. Repeating that same pure command returns the same receipt. This is
not a claim of generic invocation idempotency or persistent simulated CRM state.
Engine remains responsible for activity replay. An uncertain invocation must be
recovered from the native session/execution API before a manual retry.

Browser voice is chained: microphone PCM → SDK STT → user-reviewed draft → the
same chat endpoint → authorized completed execution text → SDK TTS. Transcription
does not dispatch the agent automatically. Raw audio and transcripts are not
persisted by the application. Voice costs run outside Engine model budgets.
The existing [quiet-room limit](0023-quiet-environment-demo-voice.md) still applies.

## Consequences and tradeoffs

- At most three specialist visits, one each, and seven model calls per execution;
  no parallel tool calls or automatic model/tool retry.
- User input: 4,000 characters; projection: 16 SDK items/24,000 serialized characters.
  The browser retains at most 20 transient messages, not a durable transcript.
- PCM: mono 24 kHz signed little-endian 16-bit, 0.25–15 seconds, 970,000-byte HTTP
  upload bound. TTS output: at most 120 seconds. Eight admitted HTTP requests is
  the existing process bound; no production rate/capacity claim is made.
- Stopping browser waiting or playback does not claim to cancel accepted Engine
  work. Native status recovery and bounded polling remain available.
- Project policy is shared with other workspaces. The required four `telco_*`
  allowlist additions were explicitly authorized and applied;
  [Phase 2 runbook](../runbooks/PHASE_2.md) records the exact proposed change.

## Alternatives considered

Direct provider calls from hosted agents would bypass the chosen Engine model
owner. A second SDK session/run/approval store would duplicate platform ownership.
General continuation requires a broader provider bridge. Those options are not
used. Persistent simulated account changes would require a separate service-owned
schema and permission decision; this increment uses pure simulation receipts.

## Validation

[VERT-001/002 evidence](../tasks/VERT-001-JOURNEY.md) separates local SDK/HTTP/browser
checks from pending live Engine replay, resume, isolation and voice acceptance.
Passing doubled transport tests is not hosted compatibility or routing-quality proof.

Official SDK orchestration reference:
https://developers.openai.com/api/docs/guides/agents/orchestration

Official voice architecture reference:
https://developers.openai.com/api/docs/guides/voice-agents

Engine invoke/execution contracts were inspected in its official OpenAPI schema.
Pinned runtime: OpenAI Agents SDK 0.24.0, OpenAI 3.40.0, Engine SDK/runner 0.11.11,
Python 3.15.2. Existing locks retain the separate hosted and application runtimes.

## Revisit trigger

Revisit after the live resume/replay and multi-agent memory gates, when official
OpenAI adapter support appears, or before adding persistent simulated account
mutations or widening the quiet-room demo scope.
