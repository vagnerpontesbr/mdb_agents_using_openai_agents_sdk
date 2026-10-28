# Telecom customer-service agent asset requirements

## Objective

Deliver an executable, adaptable reference for architects, developers, and builders: a uv-managed Python backend, React frontend, MongoDB persistence, and OpenAI Agents SDK orchestration. The current stage is research and planning, not application implementation.

## Requested capabilities

- Target the latest stable Python release; verify compatibility rather than silently selecting an older release.
- Target MongoDB 9 and validate required deployment/search capabilities.
- One customer-service supervisor and three specialists: financial, technical, and sales, including upsell and cross-sell.
- Chat and voice in the initial delivery, with shared identity and conversation continuity.
- Persistent memory using MongoDB Agent Engine's memory framework, taking mem0 as a conceptual reference.
- Prepare deployment to MongoDB Agent Engine; validate its runtime contract with OpenAI Agents SDK.
- Prefer MongoDB Auto Embedding wherever the required model/workflow is supported; document direct Voyage exceptions.
- Semantic cache with expiration, invalidation, tenant isolation, and protection against private or stale transactional data reuse.
- Voyage Matryoshka embeddings: voyage-context-4 for technical knowledge, voyage-4 and voyage-4-lite elsewhere as appropriate.
- voyage-context-4 auto-chunking, preserving provenance and validating quality.
- Hybrid retrieval using MongoDB native rank fusion and Voyage reranking.
- PDF operational procedures and an ingestion tool associated with the technical specialist, restricted to authorized curators.
- Prefer OpenAI ingestion when it fits the requested external storage/embedding pipeline; otherwise use IBM Docling.
- React inspired by MongoDB visual identity, presented as an independent reference asset.
- Documentation, synthetic data, configuration, and working installation/build/run/adaptation commands.
- Codex repository guidance, documented decisions, verifiable tasks, and acceptance criteria.
- Individual ADRs and an indexed decision section covering context, alternatives, consequences, status, and validation.
- Document governance: information owner, creation/ingestion/expiry/review dates, applicability, approval, lineage, and explainable risk scoring.
- Synthetic high-risk outdated SOP demonstrating excellent stale-reference RAG metrics but an incorrect current business outcome; compare with governed retrieval and independent time-valid evaluation.
- An English best-practices guide covering architecture, framework/platform separation, token economics, guardrails, governance, evaluations, operations, and recovery.
- Justified independently scalable service boundaries and isolated ingestion workloads, with reproducible capacity, stress, and resilience tests. Do not infer production readiness from the asset or from mock-provider benchmarks.
- Predictable response contracts: typed model outputs, deterministic backend decisions, versioned templates for critical financial/commercial/action responses, and repeated-run evaluations. Do not claim identical LLM generation or conflate repeatability with current factual correctness.

## Language — latest user instruction

Everything is in English: planning, documentation, code, agent instructions, navigation, interface, sample data, chat, and voice. This supersedes the temporary Portuguese-interface request.

## Proposed assumptions

- Browser chat and browser voice initially; telephony/SIP requires a separate integration decision.
- Synthetic customer data and simulated CRM, billing, and provisioning adapters.
- Locally executed application connected to MongoDB Atlas; Engine deployment subject to its runtime compatibility gate.
- Demonstration actions have simulated business effects.

## Explicit future extension — out of scope

Formal intent catalogs, knowledge ontologies, and a dedicated intent-classification/context-routing subsystem are not included in this asset. They may later improve routing consistency, but do not establish end-to-end determinism on their own. Current supervisor/specialist routing, structured outputs, governance, and deterministic business/template boundaries remain in scope.

## Four planning roles

1. OpenAI Agents SDK assessment.
2. MongoDB Agent Engine, memory, deployment, and search assessment.
3. Complementary architecture: Voyage, ingestion, frontend, operations.
4. Integrated review, recommendations, and implementation plan.

The first three research in parallel; the fourth reviews findings after an auxiliary-agent slot becomes available.

## Selected data architecture

Use MongoDB as the integrated operational/full-text/vector data platform to reduce separately operated engines and synchronization pipelines. Use exactly one Atlas cluster; segregate environment/service-domain databases and service-owned collections with least-privilege identities. Enforce tenant/ACL isolation in shared collections. Align application configuration, backing services, stateless processes, releases, and administration with Twelve-Factor; do not claim that Twelve-Factor or namespace names provide isolation. Validate same-cluster Engine attachment and preserve managed namespaces.

The canonical project creation plan is `initial_plan.md` at the project root.

## Codex implementation foundation

Use root AGENTS.md, bounded task records, contribution/review guidance, and executable repository checks. Intended GitHub repository: https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk. Authored workflow files do not establish remote configuration or successful CI. Preserve remote work when access becomes available.

Include explicit typed function-calling examples for invoices, authorized ingestion jobs, and approved simulated plan changes. Evaluate semantic response quality with calibrated offline LLM judges and independent current references; online judge gating is optional, not an SDK-provided correctness guarantee.
