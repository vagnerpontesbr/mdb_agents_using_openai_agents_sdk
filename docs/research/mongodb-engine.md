# MongoDB and Atlas Agent Engine research

Research context: this document informed the original design. For current implementation, accepted limitations and tested versions, use the [Phase 0 checkpoint](../compatibility/PHASE_0.md); for operating the bounded demo, use the [demo runbook](../runbooks/DEMO.md). Research proposals are not evidence of implemented full-application behavior.

Research date: 2026-10-28. Planning only; official pages were opened and read through Chrome because shell DNS was unavailable. No infrastructure was provisioned and no integration was executed.

## Verified findings

| Topic | Evidence and consequence |
|---|---|
| MongoDB 9 | Official release notes identify the **9.0 series as the current stable release**. Keep MongoDB 9 as requested; pin a verified patch/image digest during implementation. This does not verify the Engine bundled local image version. |
| Engine maturity | Atlas Agent Engine is **Public Preview**, intended for evaluation/prototyping, with no availability SLA/SLO and possible breaking changes. Appropriate for this example asset, but do not describe its deployment profile as production supported. |
| Engine framework contract | The contract explicitly documents **LangGraph/LangChain through `agent-engine-sdk-langgraph`**. It does not establish native OpenAI Agents SDK support. Provider support for OpenAI via LangChain `ChatOpenAI` is not support for the OpenAI Agents SDK orchestration runtime. |
| Deployable entrypoint | Engine imports a module-level `App`; `@app.entrypoint`, registered tools, `app.run()`, and `agent.yaml` pointing to `module.path:attribute`. Agents do not implement their own HTTP endpoint. Local settings belong in `dev.yaml`. |
| Execution guarantees | Tool and LLM calls must go through `app.tool(...)` and `app.llm(...)` for Engine audit/policy/replay. Calls outside these wrappers are not audited and do not replay correctly. `app.llm` registration must happen while entrypoint is on the call stack. State must be JSON/BSON serializable. |
| Memory | The official independent Python package is **`agent-engine-sdk-memory`**, imported as `agent_engine_sdk_memory`. Standalone external applications are explicitly supported, both hosted and local. This provides a valid integration path for the OpenAI Agents SDK without claiming Engine execution compatibility. |
| Hybrid retrieval | Native `$rankFusion` is documented for MongoDB **8.0+**; it executes ranked selection pipelines over **one collection**, deduplicates, and performs weighted reciprocal rank fusion. `$search` and `$vectorSearch` are allowed. Project/transformation stages belong after fusion. Separate search and vector indexes are required for the proposed hybrid pipeline. |

## Memory architecture

Use Engine memory as the authoritative conversational memory service. Mem0 is a design reference for extraction, reconciliation and retrieval; do not add a competing Mem0 persistence/extraction service by default. MongoDB lists the Mem0 and OpenAI Agents SDK integrations as community maintained, distinct from the Engine contract.

Memory lifecycle: chronological short-term turns → asynchronous snapshots → LLM extraction into durable memory. Durable memory is eventually available, not guaranteed on the next turn; immediate context uses STM.

| Type | Telecom example | Default visibility |
|---|---|---|
| Semantic | Preferred contact channel | Private user |
| Episodic | Previous outage resolution and outcome | Private user |
| Procedural | Reusable workflow learned for the user | Private user |
| Taxonomic | FTTH/ONT/LOS terminology | Shared project |

All records are isolated by project. `build_context` defaults to semantic and episodic sources; STM, procedural and taxonomic require explicit `enabled_sources`. Context assembly ranks, deduplicates and trims to a token budget. Approved operational SOP documents remain in the separately governed knowledge base; a learned procedural memory must not silently replace an approved SOP.

The standalone guide documents `Memory`, `MemoryRequestContext`, `record_turn`, `build_context`, `search`, and per-type save/read operations. Hosted examples use `service_account_token`, `project_id` and platform `base_url`. Local examples use the local orchestration-engine URL **without project_id or access token**. Do not mix illustrative constructors from different documentation versions; pin the tested SDK contract.

Documented standalone baseline: Python >=3.11, CLI >=0.1.120, SDK example pinned to **0.11.8 from PyPI** (guide warns the Engine package registry currently serves an older SDK). These are source baselines, not proof that those releases are the newest. Resolve and lock the validated implementation versions with uv.

Hosted memory requires an M10+ Atlas cluster according to the memory guide, project ownership, the documented database permissions, Voyage credentials, extraction LLM credentials, and Engine network access. Tokens require renewal. The M10+ condition belongs to the Engine memory profile; do not generalize it to all Atlas Vector Search deployments.

Local `agentengine create --memory-only` produces `project-config.yaml`. `agentengine dev up` starts MongoDB, memory-server and an orchestration-engine proxy. It supports built-in memory types; custom memory types are unavailable locally. The bundled MongoDB version and compatibility with a requested MongoDB 9 external instance must be verified before claiming local parity.

## Automated Embedding: use wherever compatible

Official Auto Embedding is confirmed. MongoDB generates document embeddings asynchronously on insertion/update and query embeddings from text. An index uses `type: autoEmbed`, `modality: text`, a text `path` and a supported `model`; query through `$vectorSearch` with `query` text. Python driver index management is documented for PyMongo 4.7+.

Supported models on the opened pages: `voyage-4-lite`, `voyage-4`, `voyage-4-large`, `voyage-code-4`, `voyage-code-3`. **`voyage-context-4` is not listed**, so retain the requested contextual API pipeline for the SOP knowledge base. Do not silently replace its model merely to enable Auto Embedding.

AutoEmbed supports `numDimensions` **256, 512, 1024 or 2048**, default 1024; quantization is separate and defaults to scalar. One index cannot mix `vector` and `autoEmbed` fields. Indexes can include filter fields for tenant, user, scope and revision constraints. Fields indexed as autoEmbed must be queried with `$vectorSearch`; the `$search` vectorSearch/knnBeta operators cannot query them. Hybrid lexical retrieval uses a separate lexical index and a `$search` branch alongside `$vectorSearch` under native `$rankFusion`.

Proposed use:

- Semantic cache: AutoEmbed with `voyage-4-lite`, starting at 512 dimensions, gated by retrieval quality evaluation. Strict tenant/user/authorization/context/version filters; inspect expiry in application logic as well as TTL cleanup. Indexing lag means a newly inserted entry can miss temporarily.
- Additional application-owned semantic retrieval: AutoEmbed with `voyage-4`, starting at 1024 dimensions, tune against measured recall. Make dimension profiles explicit and versioned, not uncontrolled slicing across models.
- Knowledge base: manual `voyage-context-4` contextual embedding/auto-chunking pipeline, because the supported AutoEmbed list does not include it; native MongoDB vector storage/search and fusion still apply.
- Engine memory: let the official memory service own embeddings and indexes. The standalone configuration exposes `memory.voyage.model` and `dimension`; its example uses voyage-4-large/1024. Configure requested voyage-4 only after service validation. **No opened Engine source proves it can use AutoEmbed internally**; do not rewrite its managed collections or add a second embedding writer. This is an explicit exception to “where possible,” pending an official capability.

Do not equate Auto Embedding with auto-chunking: text over 32,000 tokens is truncated during indexing, while over-limit query text fails. Ingestion must validate document/chunk token sizes. Changing model/dimensions/quantization rebuilds the index and regenerates embeddings. Default scalar quantization and a Matryoshka dimension choice are different optimizations.

Operational facts: dedicated Atlas clusters require storage auto-scaling; embeddings persist in a separate internal database/collection on the cluster; index readiness/lag must be monitored. The read Atlas documentation says inference occurs on MongoDB-managed Google Cloud infrastructure in a US region regardless of the cluster provider; document this for customer deployment/data-residency decisions. Self-managed options exist, but deployment prerequisites were not fully validated in this planning pass. `voyage-code-4` is Atlas-only according to the model page.

## Architecture decision and blocking proof of concept

Keep the OpenAI Agents SDK as the core framework and integrate the standalone Engine memory client through a small application adapter. Provide a local backend/React profile first. Isolate an Engine execution adapter as an additional profile with a blocking compatibility proof of concept:

1. Establish an officially supported adapter contract or document an explicit experimental bridge. Do not silently replace OpenAI orchestration with LangGraph.
2. Demonstrate every LLM/tool call, streaming event, interruption, checkpoint and resume through the platform contract; embedding calls and specialist execution also require examination.
3. Verify audit and policy enforcement, resume without duplicate financial/sales actions, and single ownership of session/memory turn recording.
4. Validate the exact Python latest-stable version across OpenAI SDK, memory SDK, Engine build/runtime and Docling. Python >=3.11 in documentation does not prove latest-version wheel compatibility.
5. Run feature probes against MongoDB 9 for native fusion, lexical/vector indexes, AutoEmbed text queries, filter isolation, index readiness and chosen dimension profiles.

Until these pass, label the asset **Engine memory integrated; Engine execution adapter planned/experimental**, not fully Engine deployable. The React API gateway is separate from the imported Engine agent entrypoint.

## Official sources opened

- MongoDB releases: https://www.mongodb.com/docs/manual/release-notes/
- Engine overview: https://www.mongodb.com/docs/agentengine/
- Engine contract: https://www.mongodb.com/docs/agentengine/reference/agent-contract/
- Memory types: https://www.mongodb.com/docs/agentengine/add-features/memory-types/
- Standalone memory: https://www.mongodb.com/docs/agentengine/add-features/memory-only/
- Native rank fusion: https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankFusion/
- Integration catalog: https://www.mongodb.com/docs/atlas/ai-integrations/
- Auto Embedding overview: https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/
- Auto Embedding models: https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/models/
- AutoEmbed index schema and Python setup: https://www.mongodb.com/docs/vector-search/indexes/vector-search-type/
