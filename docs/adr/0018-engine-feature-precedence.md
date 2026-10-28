# ADR-0018: Prefer Agent Engine for overlapping platform capabilities

- Status: Selected by explicit user instruction; integration verification pending
- Date: 2026-10-28
- Owner: Repository implementation
- Refines: [ADR-0001](0001-framework-platform.md), [ADR-0003](0003-memory-state.md), and [ADR-0007](0007-budgets-guardrails.md)

## Context

The user stopped the planned custom adapter prototype and requested a feature comparison, selecting Agent Engine whenever it overlaps with OpenAI Agents SDK. Platform ownership must be settled before implementing a bridge. OpenAI Agents SDK remains the selected orchestrator; similar feature names do not establish equivalent contracts.

## Decision

Agent Engine is authoritative for overlapping platform capabilities. Do not implement a competing SDK/application memory store, approval service, replay engine, platform policy engine, or primary execution trace store. SDK interfaces may translate requests and results; they must not become independent owners or bypass Engine controls. If the required integration is unavailable, keep that capability blocked and document the gap instead of silently falling back. This rule takes precedence over earlier proposed application-owned run/approval persistence.

Keep Agent/Runner and the supervisor/specialist composition in OpenAI Agents SDK. Keep business authorization, document validity, exact-action binding, monetary calculations, templates and idempotency in backend code: these are domain obligations, not substitutes for Engine controls. Preserve the shared Anthropic memory model, injected credential and gateway configuration used by geo-intelligence-network and the two-cluster boundary. No shared project configuration changes are part of this decision.

## Feature ownership and comparison

Scope: the asset's Python SDK capabilities, reviewed against official documentation on 2026-10-28 and the pinned package inspection in [COMP-003](../tasks/COMP-003-HOSTED.md): openai-agents 0.24.0 and Engine SDK/runner 0.11.11. Current documentation is not proof that every feature works in these pinned versions or through this integration.

| Capability | OpenAI Agents SDK surface | Engine overlap | Selected owner and remaining boundary |
|---|---|---|---|
| Conversation history | Session interface, explicit history, provider continuation IDs | Memory SDK conversation turns/short-term memory [M] | Engine persistence; translate SDK items only as needed. Ordering, tool correlation, trimming and concurrency need separate acceptance. Do not add a second session database or provider-owned conversation as another authority. |
| Long-term memory/context | Session history alone is not a semantic extraction service | Semantic, episodic, procedural and taxonomic memory [M] | Engine exclusively. Bounded STM/durable retrieval passed; retention/deletion and application tenant authorization remain open. |
| Model calls | Model/provider interfaces | Runtime LLM wrapper/proxy [S] | Engine-mediated model execution for hosted runs; retain requested providers. SDK model objects are bridges, not alternate credential/routing policy owners. Gateway reachability alone does not establish OE enforcement. |
| Tool execution | FunctionTool, typed schemas, function_tool | Runtime tool wrapper, tool/model allowlists [S, P] | Engine controls execution; SDK exposes schemas and translates calls. Backend validates domain actions. No direct fallback after Engine denial, interruption or timeout. |
| Remote MCP | SDK MCP integrations | Engine remote MCP connections [C] | Engine connection/execution management where supported. Documented streamable HTTP support does not establish every SDK transport or hosted-tool equivalent. |
| Content guardrails | Input/output/tool guardrails | Project/workspace model input/output guardrails [G] | Engine for matching content controls. Arbitrary SDK tool checks and domain validations are not automatically equivalent to Engine model-stage guardrails. Keep domain checks in backend code. |
| Execution limits | max_turns and SDK/model settings | Tool/LLM allowlists, call counts and duration budgets [P] | Engine platform budgets. SDK max_turns can remain a local loop bound, never the policy authority. Application tenant quotas and external OCR/voice costs need explicit coverage; do not assume Engine budgets include them. |
| Human approval | needs_approval, interruptions, RunState | Suspend/review/resume lifecycle [H] | Engine owns approval lifecycle and durable checkpointing. SDK state, if required, is translated inside that lifecycle. No separate approval database/workflow. Approver identity, action parameters, expiry and business eligibility remain backend checks. |
| Replay/recovery | Serialized SDK run state is not platform durable replay | OE stored step results and checkpoint resume [H] | Engine owns replay. Stable operation identity and SDK state restoration remain unproved. Business idempotency is still required for uncertain external outcomes. |
| Execution observability | Tracing, RunHooks, AgentHooks | Traces for LLM/tool/memory/policy/guardrail/review steps [T] | Engine is primary execution trace authority. Correlate application diagnostics without duplicating sensitive payloads or enabling an independent SDK trace export by default. Hooks are not enforcement. |
| Supervisor/specialist flow | Agent, Runner, agent.as_tool, handoffs [O] | Platform agent-to-agent calls appear in traces [T] | Keep the selected in-process SDK orchestration. Remote agent calls are not equivalent to local handoffs/as_tool and do not justify extracting specialists. If remote delegation becomes necessary, prefer Engine transport and validate the mapping. |
| Structured outputs | Typed output schemas and tool arguments | Content output validation [G] | Retain SDK schema contracts and deterministic backend checks; Engine content filtering is not a proven replacement for typed parsing or factual correctness. |
| Streaming, voice, evaluation | Streaming events, voice pipeline and evaluation integrations | No equivalent end-to-end contract established by this review | Preserve separately scoped probes; do not claim parity or move these features on the basis of names alone. Prefer Engine if an actual overlapping capability is subsequently established. |
| Hosting/secrets | SDK orchestration is not a hosted control plane | Engine runtime and deployment [S] | Engine target; Linux, packaging and hosted SDK compatibility remain blocked. |

## Alternatives considered

Duplicate each platform capability in the SDK/application; continue the custom adapter before agreeing ownership; or replace the selected orchestrator. The user selected Engine precedence while the existing orchestration requirement remains in force.

## Consequences and tradeoffs

The intended bridge becomes translation only. Engine's documented framework adapters are LangGraph and Google ADK; no ready OpenAI adapter was established. The documented human-review example uses LangGraph interrupt/checkpoint behavior, not OpenAI RunState. Internal runner extension interfaces are not a supported application adapter. Therefore Engine feature availability does not imply this asset can use it yet. The user subsequently authorized a custom adapter under this ownership rule. The [bounded implementation](../../compatibility/openai_engine_adapter/README.md) implements a local BaseAgent/Runner bridge for a single text/model/read-tool request. It uses Engine proxies and does not register replacement workflow, memory or approval owners. Local contract tests do not establish hosted support; deployment and platform settings remain unchanged.

## Validation before acceptance

For each overlapping feature, prove one authoritative Engine path, correlated identity/call IDs, positive and denied outcomes, and no SDK bypass. Separately test conversation item fidelity, approval rejection/stale decisions, replay after interruption, budget exhaustion and guardrail blocking before output release. Distinguish local doubles, pinned interface inspection and live Engine evidence. Preserve the [Phase 0 gates](../compatibility/PHASE_0.md); this documentation decision does not complete a phase.

## Sources

- [O — Official OpenAI SDK feature mapping](https://developers.openai.com/cookbook/examples/agents_sdk/migrate-from-claude-agent-sdk/readme): Runner, tools, sessions, hooks, guardrails, approvals and specialist ownership.
- [S — Engine Python SDK catalog](https://www.mongodb.com/docs/agentengine/sdk/python/) and [base contracts](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk/docs/api/); pinned source inspection is recorded in COMP-003.
- [M — Engine standalone memory SDK](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/).
- [P — Engine Policy Engine](https://www.mongodb.com/docs/agentengine/manage/governance/policy-engine/).
- [G — Engine content guardrails](https://www.mongodb.com/docs/agentengine/manage/governance/guardrails/).
- [H — Engine human-in-the-loop execution](https://www.mongodb.com/docs/agentengine/deploy/human-in-the-loop/).
- [T — Engine execution traces](https://www.mongodb.com/docs/agentengine/manage/inspect-traces/).
- [C — Engine remote MCP](https://www.mongodb.com/docs/agentengine/add-features/remote-mcp/).

## Revisit trigger

Reassess when official adapter support or tested contracts change. Any exception to Engine precedence requires an explicit user decision; an integration failure is not an implicit exception.
