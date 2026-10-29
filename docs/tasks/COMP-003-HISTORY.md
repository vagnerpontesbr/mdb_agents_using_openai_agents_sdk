# COMP-003: chronological Engine history diagnostic

Status: **outside demo scope by user decision** under [ADR-0021](../adr/0021-demo-semantic-episodic-continuity.md); SDK restoration remains unsupported, but no longer blocks Phase 0. Bounded read-only diagnosis, including execution logs, completed on 2026-10-29. The acceptance requirements below are historical diagnostic criteria, not current demo gates.

## Acceptance and evidence

A known completed Engine session must expose a nonempty chronological transcript,
including stable tool-call/result correlation, before an SDK history translator is
implemented. The Engine remains the only memory owner. Semantic/episodic context
retrieval does not establish chronological transcript restoration.

The public `GET /api/v1/projects/{id}/sessions/{session_id}/messages` endpoint was
read for synthetic session `phase0-expiry-memory-valid-20261029`, workspace
`ws-6ae20f53f3b040aa65fa961a`, project `67b385a7976edf15ecc62e06`.
It returned HTTP 200 with exactly this structural evidence:

```json
{"messages": [], "latest_status": "completed", "history_status": "ready", "outcome_supported": true}
```

This is not a usable transcript despite the successful HTTP status. No memory
write, deployment, or policy change was performed. A second session has not been
tested by this diagnostic; the result is specific to this known session.

Pinned Engine SDK/runner 0.11.11 provides `SessionMessage.tool_calls`,
`tool_call_id`, and outcome classification. Its `SessionMessagesResponse`
documents chronological ordering. `TenantRuntime.register_query_plugin` and
`agent_engine_runner_shared.server.query.AERQueryPlugin` provide framework-specific
read hooks; AER query routes return 501 when no plugin is registered. The custom
OpenAI adapter does not register that plugin. The public gateway's empty response
does not prove the underlying reason or that adding a plugin alone is sufficient.

The gateway OpenAPI response schema currently omits `outcome_supported`, although
the live response includes it. Missing classification is rejected by the probe.

## Reproduce

Inject `AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN` into the environment without logging it:

```sh
python3 scripts/check_engine_history.py --project 67b385a7976edf15ecc62e06 --workspace ws-6ae20f53f3b040aa65fa961a --session phase0-expiry-memory-valid-20261029
python3 -m unittest tests.compatibility.test_engine_history -v
```

The first command exits 2 when blocked. It limits response size and duration,
rejects redirects, and reports structural evidence without message content or
credentials. An `observed` result only means a candidate transcript was found;
it explicitly does not claim SDK compatibility.

Validation: all six diagnostic unit tests passed under local Python 3.14.6 and
the pinned uv Python 3.15.2 environment. `python3 scripts/check_repository.py`
passed (54 Markdown files, 19 ADRs at the time of this check). Running the actual
probe through uv with the injected `.env` reproduced
`completed_session_has_no_history` and exit 2.

## Remaining integration gate

Identify an Engine-owned, workspace/session-scoped transcript source for this
custom framework and preserve its durable replay semantics. Then prove faithful
translation into the pinned OpenAI Agents SDK 0.24.0 input, including exact tool
call IDs, no orphan results, cancelled/interrupted outcomes, and bounded context.
Historical tools must not execute again. Preserve Engine order rather than
sorting persistence timestamps; do not elevate stored system/developer messages
into current instructions. Do not add SDK Session persistence or a second writer.

References: [Engine public OpenAPI](https://www.mongodb.com/docs/api/doc/agentengine.json),
[OpenAI function-call/result format](https://developers.openai.com/api/docs/guides/function-calling#handling-function-calls).
The OpenAI documentation was searched and fetched; it requires each result's
`call_id` to match its original call. No provider translation is claimed here.

## Deeper STM and durable-source investigation

The pinned SDK exposes a concrete Engine-owned read source:
`Memory.build_context(enabled_sources={"stm"}, format_style="openai",
include_memories=True, max_tokens=4096)` and its per-source counterpart with
`SourceSpec(source="stm", mode="text", top_k=20)`. Both were called read-only
for the same known synthetic session/user, with private visibility. Neither
calls `record_turn` or directly accesses MongoDB.

Live results on 2026-10-29:

| Read path | Selected STM turns | Missing transcript information |
| --- | --- | --- |
| Legacy context | user sequence 1, tool sequence 3, assistant sequence 2 | Assistant calls contain only count, names, IDs; no arguments. Tool metadata has no `tool_call_id`. |
| Per-source text context | user sequence 1, tool sequence 3 | Assistant call omitted; tool correlation absent. |

Both OpenAI-format results contain a `system` message for retrieved tool
content. It must not be promoted to a current instruction. The selected-memory
order is a retrieval order, not a chronological transcript. Sorting sequence
numbers cannot restore missing calls, arguments, result IDs, or outcome status.

The assistant chunk's `metadata.tool_calls` is a summary object with
`tool_calls_count`, `tool_names`, and `tool_call_ids`; it is not the original
call list. This explains why merely translating STM roles is insufficient.
The pinned context model documents ranking/budgeting and exposes no authoritative
transcript-completeness or cancelled/interrupted-outcome contract.

The runner's native `workflow.memory` projection preserves `MemoryToolCall`
arguments and `ToolMemoryTurn.tool_call_id` on writes. Thus the adapter already
passes call IDs into Engine-owned execution, but the tested context read projection
does not expose them losslessly. The pinned workflow client exposes per-execution
activity start/outcome, memory, finalize and completion operations; it does not
provide a cross-execution session-transcript reader. The captured public OpenAPI
has POST-only `/memory/turns`, not a GET turn reader. Existing AER query-plugin
hooks alone do not supply the missing read source.

Reproduce the comparative diagnostic (two read requests, bounded context budget):

```sh
uv run --project compatibility/hosted-runtime --frozen --no-sync --env-file .env python scripts/check_engine_stm_history.py --project 67b385a7976edf15ecc62e06 --session phase0-expiry-memory-valid-20261029 --user phase0-expiry-memory-user-valid-20261029
python3 -m unittest tests.compatibility.test_engine_stm_history -v
```

The actual script reproduced both structural gaps and exit 2. All three new
tests passed. It prints no message contents, arguments, credentials or call IDs.
This diagnostic intentionally cannot report restoration success.

The concrete remaining dependency is an Engine-supported read projection of its
already-owned STM turns, preserving original assistant call arguments, exact
tool-result IDs, ordered session scope, and outcome/completeness metadata. Once
available, an AERQueryPlugin can read it and a bounded translator can be validated.
Adding a parallel writer or guessing result IDs would violate the architecture
and cannot repair this compatibility gap. No production history helper was
introduced because neither tested public read path meets that contract.

## Structured execution-log follow-up

The official public OpenAPI also documents
`GET /api/v1/projects/{id}/execution-logs` under **Observability**, scoped by
`session_id` and `workspace_id`, with an optional opaque `after` cursor.
This source was read alongside the authoritative execution record for the
completed synthetic demo-auth execution
`006266d5-8dbe-4dfd-bc1b-f6283d5c5388`, session
`demo-invoice-ce2182a37dc342189044daf5d78c8a2f` in the workspace above.

The live response contained five logs and `has_more=false`: one memory row,
LLM start/success at step 1, and tool start/success at step 2. Structural
comparisons passed for all of the following:

- The LLM call ID matched both tool-log call IDs.
- The LLM tool name matched both tool-log names.
- The LLM arguments matched the tool-start inputs.
- All LLM/tool rows matched the execution's organization, project, workspace,
  session, execution and user scope.
- The completed execution result and tool output were equal after JSON parsing.
  Their raw strings differed, so byte-for-byte equality is not claimed.

This is stronger correlation evidence than the tested STM projection, but it
is one completed, approved, single-tool execution. `has_more=false` establishes
the end of this log response, not a lossless session transcript contract.
The inspected route does not establish transcript completeness, cross-execution
chronology, redaction behavior, or interrupted/cancelled outcome reconstruction.
It also does not validate hosted SDK continuation. No model-log system messages
were reused as instructions and no SDK translator or additional writer was added.

The read-only diagnostic ran in the frozen agent-runtime environment on
2026-10-29 and printed structural types and comparison booleans only. It used
the existing private CLI identity; no credential, message text or tool payload
was recorded here. No deployment or shared configuration changed.

The user subsequently narrowed demo acceptance to the already-tested semantic/
episodic continuity in ADR-0021. This is a scope change, not proof of transcript
support; no further history investigation is required for the demo.
