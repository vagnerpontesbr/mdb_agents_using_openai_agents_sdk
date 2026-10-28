# Best Practices for the Telecom Agent Asset

This is the architecture and implementation guide for the planned asset. Controls below are planned unless explicitly backed by a completed test or artifact; documentation does not establish production readiness. See the [plan](../initial_plan.md), [ADRs](adr/README.md), and [document governance specification](DOCUMENT_GOVERNANCE.md).

## 1. Separate agent framework from agent platform

The framework defines agent orchestration, typed tools, handoffs, and workflow contracts. The platform supplies hosting, identity, memory services, secrets, policies, audit, and operations. OpenAI Agents SDK is the selected orchestration framework; MongoDB Agent Engine is a platform integration target. An OpenAI model provider adapter is not proof of SDK runtime compatibility.

Keep platform dependencies behind explicit adapters; independently prove memory and hosted execution support. Preserve required audit/replay wrappers. Avoid an abstraction that promises identical semantics across incompatible runtimes. Record supported capabilities and fail clearly for missing ones.

## 2. Use justified service boundaries

Separate ingress/API, interactive agent execution, knowledge retrieval/governance, and asynchronous ingestion workers into independently runnable processes with versioned contracts. Isolate CPU/memory-heavy OCR from interactive latency and bound each workload's resources. Voice transport can start in the ingress service and separate when concurrent audio streams justify it.

Keep supervisor and specialists in one agent-runtime service initially. A specialist is not automatically a microservice. Extract CRM/BSS/OSS connectors only for independent security, scaling, ownership, or release needs. Avoid building a distributed monolith of synchronous calls.

Each service owns writes to its collections; other services use its contract. Sharing a MongoDB cluster initially is acceptable but does not remove resource contention. The knowledge service owns document governance, chunks, publication, and retrieval cache; ingestion submits staged versions through its internal contract. Engine owns managed memory. Agent runtime owns run/approval state. Use least-privilege service credentials and observe pool sizes across replicas.

## 3. Scale without losing correctness

Stateless replicas retain session state externally. Serialize or version concurrent turns per conversation, using leases/fencing or compare-and-set to prevent conflicting writers. Keep idempotency keys bound to tenant, operation, and parameters. A network timeout does not establish whether a business action happened: reconcile status before retrying.

Use bounded queues, consumer leases, visibility timeouts, retry limits, dead-letter handling, and idempotent consumers. Delivery is at least once; do not claim exactly-once execution. Use an outbox or equivalent atomic persistence for state changes plus emitted events. For the initial small deployment, MongoDB-backed jobs with atomic claims are a candidate; adopt a dedicated broker if measured throughput/operations warrant it.

Configure deadlines across dependency chains, exponential backoff with jitter only for eligible failures, circuit breakers, per-provider concurrency limits, per-tenant quotas, and load shedding. Do not amplify overload with nested retries. Drain streaming connections and workers during shutdown; preserve resumable state. Test queue age, not only queue length.

## 4. Token economics and cost controls

Account for supervisor and specialist input/output, repeated history, tool outputs, memory extraction, embeddings/re-embedding, reranking, STT/TTS, and infrastructure. Model pricing and units are versioned configuration, never hard-coded assumptions. Attribute costs by tenant, conversation, workflow, and component.

`conversation_cost = sum(model_input + model_output + embedding + rerank + audio + memory_processing) + allocated_infrastructure`

Each term uses actual billable units and the dated provider rate. Avoid double-counting memory-service embedding usage or treating semantic cache hits as provider prompt-cache hits. Track cost per successfully resolved conversation, not only cost per request.

Limit turns, tool calls, tokens, retrieved chunks, rerank candidates, audio duration, and wall time. Compact history while preserving tool/result pairs and provenance; retrieve only useful memory. Route models by measured task quality, cap fan-out, and avoid asking all specialists for every request. Put context in stable layouts when provider caching supports it. Use cheaper models/dimensions only when evaluations preserve the required outcome. Estimate ingest and reindex costs before bulk jobs. Budget exhaustion yields a clear fallback/escalation, never invented completion.

## 5. Guardrails and authorization

Enforce identity, tenant, ACL, tool argument validation, and business policy in deterministic backend code. Prompts are not access control. Tools use least privilege and explicit allowed actions; retrieved text, user uploads, tool outputs, and memory are untrusted input. Restrict file types, sizes, paths, outbound hosts, and resource use; parse documents in isolated workers.

Require confirmation for relevant financial/provisioning/plan changes, bound to the exact current proposal and authenticated user. Protect against stale approvals and replay. SDK guardrails do not necessarily cover every intermediate event or every tool boundary; validate at the boundaries that matter. If a final answer needs validation, hold it before text/audio release. Test prompt injection, malicious PDFs, unauthorized tool calls, and cross-tenant retrieval.

## 6. Govern the knowledge, not only the answer

Assign an information owner, source creation and ingestion times, effective/expiry dates, review history, applicability, provenance, and approval for each document version. Ingestion time does not establish freshness. Use the versioned, explainable risk score and hard exclusions in the [governance contract](DOCUMENT_GOVERNANCE.md).

Apply governance before publication, during retrieval, and before serving cached or generated answers. A perfect citation to an expired document is still an invalid operational basis. Show risk explanations to curators, assign review tasks to owners, and retain audit lineage. Risk is a prioritization heuristic; absence of detected risk is not proof of truth.

## 7. Build reproducible ingestion and retrieval

Preserve originals, hashes, parser/chunker/model versions, canonical text, document lineage, and verified page alignment. Detect poor OCR, repeated text, missing tables, and truncated content. Quarantine incomplete processing; publish immutable versions via an active-version pointer. Test retries and partial failures.

Prefer MongoDB Auto Embedding for supported models/workflows; use contextual Voyage directly for the documented gap. Auto Embedding is not auto-chunking. Monitor asynchronous index readiness and lag. Maintain consistent spaces/dimensions/input types and separate lexical/vector indexes. Apply all authorization/governance filters to both hybrid branches and revalidate authoritative metadata after fusion. Reranking improves relevance; it cannot certify freshness or authority.

## 8. Evaluate distinct failure sources

Measure retrieval ranking, source eligibility, answer faithfulness, citations, current correctness, agent tool behavior, and actual business outcomes separately. Track abstention appropriateness, stale-source exposure, false cache hits, tenant leakage, latency, and costs. Break down by product, firmware, language, risk band, and channel.

Keep SME-approved, time-valid references independent of the ingested corpus. Version datasets and clocks; calibrate LLM judges with human review and retain disagreements. Use held-out tests, meaningful sample sizes, repeated stochastic runs, and uncertainty estimates. Synthetic examples explain failure modes; they do not establish production accuracy. The [stale-document demo](../examples/telecom/governance/README.md) deliberately exposes circular evaluation.

## 9. Manage memory explicitly

Separate transcripts, resumable execution state, and durable facts. Let official Engine memory own its storage/extraction lifecycle; adapt SDK session semantics explicitly. Handle eventual durable-memory extraction using immediate session context. Store source/scope and support correction, expiry, and deletion. Do not persist inferred preferences or untrusted instructions as confirmed facts. Keep current billing and eligibility in business systems.

## 10. Cache with context and revocation

Distinguish provider prompt caching, retrieval caching, and semantic answer caching. Each has different correctness and cost implications. Filter by tenant/access scope and relevant context; key versions of sources, prompts, policies, models, and embeddings. Recheck TTL and source validity on reads, including cached answers after a review deadline. Negative results need short, justified expiry.

Never cache authorization decisions as permanent, reuse personal transactions across users, or skip required actions. Measure false-positive matches with negation, firmware, location, and time changes. Protect hot misses against stampedes with bounded request coalescing scoped to authorized context.

## 11. Treat voice as a channel with additional failure modes

Share workflow identity and memory between voice and chat. Test codec conversion, noise, names/numbers, transcript corrections, silence, interrupted playback, reconnects, and duplicate final transcripts. Caller ID or voice similarity alone is not authentication. Keep raw audio retention disabled by default and explain recording when enabled. Spoken confirmations must reflect actual tool outcomes. Track time to useful audible response separately from acknowledgments. Do not describe chained turn-based voice as full duplex.

## 12. Observe behavior without exposing private content

Correlate tenant-safe conversation/run/tool/job/document-version IDs across services. Record timings, retries, token units, cache decisions, retrieved source versions, risk assessments, approvals, and outcome status. Trace metadata should explain what happened without exposing hidden reasoning. Redact payloads, apply access controls and retention, and avoid high-cardinality metrics labels containing customer IDs or raw prompts.

Monitor model/provider errors, queue age, index lag, memory availability, pool saturation, stale-source attempts, budget exhaustion, and per-tenant fairness. Build operational dashboards separately from customer-facing UI. Document who responds to each actionable alert.

## 13. Stress-test both capacity and correctness

Use [the stress-test design](SCALABILITY_AND_STRESS_TESTS.md). Deterministic provider doubles isolate infrastructure capacity; separately run bounded real-provider tests. Neither result substitutes for the other. Include cold/warm cache, long conversations, concurrent sessions, voice streams, and PDF/OCR load. Keep tenant isolation, source validity, idempotency, and approval checks active during overload. A fast incorrect answer is a failed test.

## 14. Engineer for reproducibility and change

Commit uv/frontend locks and record interpreter, container, SDK, model, prompt, index, and policy versions. Use contract tests for external integrations, schema validation, typed tool outcomes, and frozen installs. Separate deterministic CI, credentialed integrations, evaluation, and stress suites. Use additive API/schema changes, staged index migrations, canary runs, rollback plans, and dependency/license/security review. Never place keys in the frontend or fixtures.

Maintain concise AGENTS.md instructions with commands that actually work, small reviewable changes, and ADRs with context, alternatives, consequences, and evidence. The asset should teach adaptation while clearly identifying which integrations remain experimental.

## 15. Plan recovery and operational ownership

Define service owners, dependency failure behavior, backup/restore responsibilities, and retention. Test restoring source metadata and run state, rebuilding indexes, replaying idempotent jobs, and reconciling partially completed business actions. Assign measurable RPO/RTO targets after choosing the deployment profile; do not claim them before restore tests. Agent Engine Public Preview limitations remain visible in deployment guidance.

## 16. Constrain generation and render critical responses deterministically

Separate schema consistency, business decision consistency, and identical wording. SDK `output_type` with Pydantic constrains successful structured responses, but does not certify their values. Explicitly handle refusals, incomplete outputs, and validation failures. Agent interpretation and model-based guardrails remain probabilistic; validate parameters and clarify ambiguity before executing deterministic business logic.

Render invoices, offer conditions, approvals, and action confirmations from versioned templates using authoritative data and server-controlled currency/date formatting. Do calculations, eligibility, expiry, and authorization in code. The final response boundary must prevent later supervisor paraphrasing of protected text. For the same validated inputs, state, clock, template, and rules, expect the same result. For changed facts or policies, require updated results. Share this boundary across text and voice; TTS can vary acoustically even with identical input text.

Use grounded generation for explanatory prose, with structure, citations, and deterministic governance checks. Low temperature on supporting models can reduce variation, but neither zero temperature nor a seed guarantees deterministic LLM generation. Do not assume a seed parameter exists on every provider/API path. Pin supported model snapshots and prompt/schema/policy versions; isolate changes in evaluations. Test fixed context/tool fixtures separately from live data, and never freeze live facts merely to obtain repeatability.

Measure repeated-run schema validity, routing agreement, parameter accuracy, business decision consistency, factual correctness, and exact rendered text separately. Exact-text assertions fit templates; they are generally unsuitable for free-form explanations. A stable wrong answer, a stale semantic-cache hit, or a faithfully reproduced obsolete procedure still fails business correctness. See [ADR-0009](adr/0009-deterministic-responses.md) and [plan section 15](../initial_plan.md#15-predictable-responses-and-deterministic-business-behavior).

## 17. Consolidate the data platform while enforcing ownership

Use MongoDB for operational documents and full-text/vector/hybrid retrieval to reduce separate data products and synchronization pipelines. This is integration simplification, not a promise of one physical engine, zero internal duplication, or immediate index visibility. Recheck mutable business facts and governance authoritatively.

Use the [approved two-cluster boundary](adr/0017-two-cluster-memory-boundary.md) with service/domain databases, access-pattern collections, per-service least-privilege credentials, and isolated eval/load namespaces. Names alone do not enforce access. Tenant filters remain mandatory in shared collections. Managed Engine/Auto Embedding schemas keep their supported ownership; validate each designated cluster connection. Shared infrastructure still creates contention and recovery blast radius.

Apply Twelve-Factor to config, backing services, stateless processes, releases, dependencies, concurrency, logs, and admin jobs. It is not a database isolation standard. See the [data architecture and factor mapping](DATA_ARCHITECTURE.md), [ADR-0010](adr/0010-mongodb-integrated-data-platform.md), and [ADR-0017](adr/0017-two-cluster-memory-boundary.md).

## 18. Make Codex practices executable

Use root AGENTS.md for concise, automatically discoverable working guidance and link the detailed plan/ADRs. Maintain task scope, dependency, acceptance, and evidence separately from conversation history. The standard-library repository checker is available now; add frozen uv builds, lint/types, and behavior tests with application code. Keep real-provider and load validation separate. Review diffs and remote history before integration; distinguish authored files, local checks, commits, PRs, and deployments. See [CONTRIBUTING.md](../CONTRIBUTING.md) and ADRs 0012–0014. Global configuration and custom skills are optional, not prerequisites for this workflow.
