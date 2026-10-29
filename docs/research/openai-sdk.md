# OpenAI Agents SDK assessment

Research context: this document informed the original design. For current implementation, accepted limitations and tested versions, use the [Phase 0 checkpoint](../compatibility/PHASE_0.md); for operating the bounded demo, use the [demo runbook](../runbooks/DEMO.md). Research proposals are not evidence of implemented full-application behavior.

Documentation research: 2026-10-28. Scope: planning; no dependencies installed or paid API calls executed.

## Recommended decision

Use the Python `openai-agents` package as the orchestration runtime. The supervisor serves the customer and calls three specialists through `agent.as_tool()`: financial, technical, and sales. It owns the final response and can combine diagnosis, financial impact, and commercial offers within one interaction. Specialists return structured contracts, sources, tool results, and next steps. Handoffs remain an explicit extension for journeys where a specialist should take over the conversation; they are unnecessary for the requested supervisor pattern.

This choice is directly supported by the official [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration) documentation. Adding LangChain/LangGraph is unnecessary to execute the tool loop, call specialists, or transfer control.

## Verified capabilities

| Requirement | Official capability | Proposed application |
|---|---|---|
| Agent loop | `Runner.run()` executes models, tools, and handoffs until the final response | Reuse the runtime; bound duration, turns, and calls |
| Supervisor | `agent.as_tool()` keeps response ownership with the manager | Three specialists exposed as bounded capabilities |
| Tools | `@function_tool`, typed parameters, and structured results | Simulated CRM/BSS/OSS integrations behind replaceable interfaces |
| Streaming | `Runner.run_streamed()` and `stream_events()` | Backend converts events to SSE for React |
| Continuity | `session`, explicit history, or OpenAI-managed state | Select MongoDB-backed sessions as the single strategy |
| Pause/resume | `interruptions`, `to_state()`, approval/rejection, and same-run resumption | Persist contract and financial actions until a decision |
| Guardrails | Input, output, and tool checks | Domain rules and authorization at tool boundaries |
| Observability | Native tracing enabled by default in the server-side path | Correlate customer interactions, RAG queries, and memory |
| MCP | Hosted MCP or SDK-managed private connections | Future extension for enterprise tools |

Sources: [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents), [Results and state](https://developers.openai.com/api/docs/guides/agents/results), [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals), [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability), [migration and typed tools](https://developers.openai.com/cookbook/examples/agents_sdk/migrate-from-claude-agent-sdk/readme).

Initial voice support is covered by the separate [voice assessment](voice-agents.md), including the verified Python `VoicePipeline` approach. All demo prompts, responses, documentation, and interface copy use English.

## Memory: three independent contracts

1. **Session:** history required for the next turn. The official `SessionABC` extension exposes `session_id` and asynchronous methods `get_items(limit=None)`, `add_items(items)`, `pop_item()`, and `clear_session()`. Build an adapter to MongoDB Agent Engine memory after validating its actual API. Avoid duplicating persistence if the Engine already provides a compatible implementation.
2. **Execution state:** a serialized snapshot of an interrupted run. Persist separately from the transcript and version with the SDK; a session alone does not replace this snapshot.
3. **Durable memory:** preferences, confirmed facts, and useful episodes across sessions. Use the Engine framework and mem0-inspired semantics (extract, reconcile, update, forget), without treating every message or retrieved response as a permanent fact.

The adapter must preserve ordering, tool calls with their results, and turn boundaries; test concurrent turns within one session. Enforce tenant and customer isolation in the authenticated backend. Do not share a mutable specialist session without a clear contract: the outer transcript belongs to the supervisor; specialist runs receive minimal context and their own identifiers when needed.

The official [Context Engineering — Sessions](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory#implement-custom-session-object) cookbook supplies the custom interface and explains trimming by complete turns. Adapting it to Agent Engine is a proposed design, not a native integration verified by this research.

Use MongoDB Auto Embedding wherever the selected model, deployment, and index capabilities support it, as required by the user. Keep embedding ownership in the MongoDB integration layer rather than duplicating embedding calls inside agent tools. Unsupported combinations require an explicit, documented provider path; support must be established by the MongoDB/Voyage research.

## PDF ingestion: available capabilities and unverified assumptions

OpenAI provides real PDF capabilities:

- The Responses API accepts `input_file` and, with vision-capable models, includes extracted text and page images in model context. This supports questions and model-directed extraction: [File inputs](https://developers.openai.com/api/docs/guides/file-inputs).
- `FileSearchTool` queries files in OpenAI-hosted vector stores; the platform offers managed ingestion and retrieval: [File search](https://developers.openai.com/api/docs/guides/tools-file-search).

The consulted pages do not document a generic Agents SDK parser that exports structured documents, pages, tables, and chunks directly into a Voyage embedding and MongoDB indexing pipeline. Do not claim OpenAI cannot read PDFs; the managed path does not match the asset's required storage and embeddings.

Recommendation: a typed technical-specialist tool creates an ingestion job, and a Docling worker produces a structured document and provenance for the embedding integration. The `voyage-context-4` model and its auto-chunking must be validated against Voyage documentation by the relevant research stream. Use MongoDB Auto Embedding for this path if the required model and behavior are supported. The SDK orchestrates the tool; heavy processing runs outside the customer-service loop. Ingestion belongs to the technical domain, but execution requires a knowledge-curator identity and permission; ordinary customers can consult procedures without publishing to the corporate knowledge base.

## Reference contracts and behaviors

- **Supervisor:** identifies intent, retrieves authorized context, delegates, resolves conflicts, and presents a coherent English response. It must not invent diagnoses, balances, or commercial eligibility.
- **Financial:** checks invoices and payments, explains charges, and proposes renegotiation; real changes follow business rules, appropriate confirmation, and idempotency.
- **Technical:** retrieves procedures with document/page/version citations, correlates incidents and customer services, and opens a ticket when procedures do not resolve the issue; the administrative ingestion tool returns `job_id` and status.
- **Sales:** checks catalog and eligibility, compares plans, and proposes upsell/cross-sell; prices and conditions come from business systems, never solely from memory or cache.
- **All:** results contain an explicit status (`resolved`, `needs_information`, `needs_approval`, `escalate`), evidence, and proposed actions. These enums are proposed contracts, not SDK API names.

SDK input and output checks do not cover every boundary: the documentation states that input guardrails run on the first agent in the chain and output guardrails on the agent producing the final output. Validate tools independently. Before streaming text to the customer, decide which events may be shown; output guardrails after generation cannot undo content already sent over SSE. Show safe progress events and release validated responses when the workflow requires that guarantee.

## Versions and limitations requiring validation

- The latest Python version cannot be inferred from the date or cookbook examples. Resolve the current stable release and test `uv lock`/`uv sync --frozen` with `openai-agents`, PyMongo, Voyage, Agent Engine, and Docling. If Docling is incompatible, consider a worker with its own environment and record the exception in an ADR.
- Do not select an SDK or LLM version solely from an example. Pin actually validated versions in the lockfile and make models configurable by role.
- RunState serialization, subagent behavior, turn limits, and trace export need contract tests against the selected version.
- Full equivalence with Deep Agents (persistent planning, filesystem, skills, and code execution) has not been established here. Deliver those capabilities only when useful for customer service, with explicit contracts.
- Agent Engine memory was not validated in this research stream; use the dedicated assessment and avoid promising an unverified native adapter.

## Suggested acceptance criteria

1. Financial, technical, and commercial questions invoke the corresponding specialist; mixed requests combine specialists while the supervisor owns the final response.
2. A second turn retrieves history without duplication; a new session for the same customer can retrieve authorized durable facts.
3. Different customers/tenants never share memory, approval state, or private results.
4. A subscription action pauses, persists state, resumes after a decision, and does not duplicate effects on retry.
5. Timeouts, tool failures, turn limits, and streaming cancellation produce traceable state and clear operational responses.
6. Technical responses cite current procedures; insufficient evidence leads to requests for more information or escalation.
7. A trace correlates the supervisor, specialists, tools, retrieval, reranking, and memory, with an explicit personal-data policy.
