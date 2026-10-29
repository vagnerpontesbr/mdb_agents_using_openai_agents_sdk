# ADR-0021: Limit demo continuity to validated semantic and episodic memory

- Status: Selected by explicit user instruction; bounded hosted evidence accepted
- Date: 2026-10-29
- Owner: Repository implementation
- Refines: [ADR-0003](0003-memory-state.md) and [ADR-0018](0018-engine-feature-precedence.md)

## Context

Hosted Engine semantic/episodic retrieval and context injection passed same-user,
new-session recall and different-user negative controls. The tested chronological
read paths did not establish lossless SDK history restoration. The user explicitly
selected the already-validated semantic/episodic memory scope for this demo.

## Decision

Demo conversation continuity uses the validated Engine semantic/episodic retrieval
path. Complete chronological transcript restoration into OpenAI Agents SDK is
outside demo scope and is no longer a Phase 0 acceptance gate. This decision
supersedes earlier requirements that made that restoration mandatory for the demo.

Engine remains the sole managed-memory owner. Do not add an SDK Session store,
provider-owned conversation, parallel memory writer, or log-derived transcript
as a substitute. OpenAI Agents SDK remains the orchestrator. Native Engine
approval, interrupted-execution replay and requester authorization are unchanged.

## Alternatives considered

Keep Phase 0 blocked on a supported complete transcript reader; or infer history
from observability logs. The user selected narrower demo continuity instead.

## Consequences and tradeoffs

The demo can recall selected prior facts and episodes. It does not promise exact
turn-by-turn recall, verbatim history, immediate retrieval of every new turn, or
restoration of historical tool calls. Retrieved memory is context, not authority
for financial facts or actions. The existing bounded hosted proof does not
establish every future supervisor/specialist or application behavior.

Other Phase 0 gates remain independent: runtime credential permissions,
microphone/listening and outstanding fault controls. Native expurgo remains
accepted under the user's earlier decision.

## Validation

[Hosted memory recall](../tasks/COMP-003-HOSTED.md#hosted-model-memory-recall-passes)
records the accepted positive/negative evidence. [History diagnostics](../tasks/COMP-003-HISTORY.md)
retain the unsupported restoration findings as limitations, not pending demo work.
This scope decision changes documentation only; no runtime, deployment, credentials
or shared Engine settings changed.

## Revisit trigger

Revisit if the user requests exact transcript replay or a supported Engine
chronological read contract becomes available and is required by a new use case.
