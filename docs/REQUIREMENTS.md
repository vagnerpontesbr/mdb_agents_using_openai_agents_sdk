# Telecom customer-service agent asset requirements

## Objective

Deliver an executable, adaptable reference for architects, developers, and builders: a uv-managed Python backend, React frontend, MongoDB persistence, and OpenAI Agents SDK orchestration. Phase 0 bounded compatibility is complete; Phase 1 adds the application foundation ([FND-003](tasks/FND-003-FOUNDATION.md)); Phase 2 has passed bounded hosted and browser acceptance ([VERT-001/002](tasks/VERT-001-JOURNEY.md)); its publication and CI passed. Phase 3 bounded memory/recovery acceptance passed in [MEM-001](tasks/MEM-001-MEMORY.md). See [current evidence](compatibility/PHASE_0.md) and [publication/CI status](runbooks/REPOSITORY_SETUP.md).

## Platform feature precedence — latest user decision

Use Agent Engine whenever its capabilities overlap with OpenAI Agents SDK. [ADR-0018](adr/0018-engine-feature-precedence.md) is the authoritative ownership matrix and compatibility boundary. Keep the SDK orchestrator and backend domain enforcement; do not bypass Engine when integration is blocked. The user subsequently authorized a custom adapter under this ownership rule; scope and acceptance are tracked in [COMP-003](tasks/COMP-003-HOSTED.md).

## Demo authentication — latest user decision

Use email/password login and exactly `user`/`admin` roles. Only admins register users. Initial administrator: `admin@mongodb.com`, with the user-provided password injected privately at bootstrap. [ADR-0020](adr/0020-demo-email-password-auth.md) defines the authoritative identity contract and its integration limits.

## Requested capabilities

Voice demo acceptance is limited to a quiet environment, with bounded manual
retry for unrecognized speech, under [ADR-0023](adr/0023-quiet-environment-demo-voice.md).
Reliable recognition in noisy environments is outside the current demo scope.

The local demo retains the operator's private Engine CLI login in its backend
under [ADR-0022](adr/0022-demo-private-engine-cli-identity.md). This accepted Engine
credential exception does not waive minimum application MongoDB permissions.

Demo continuity is limited to the validated Engine semantic/episodic memory path
under [ADR-0021](adr/0021-demo-semantic-episodic-continuity.md). Complete chronological
SDK history restoration is outside demo scope and does not block Phase 0.

The user-selected requester approval and thirty-day conversation/memory retention rules are defined in [ADR-0019](adr/0019-requester-approval-memory-retention.md). Policy selection does not establish remote enforcement; [COMP-005](tasks/COMP-005-AUTH-RETENTION.md) tracks the integration gate.

- Target the latest stable Python release; verify compatibility rather than silently selecting an older release.
- Target MongoDB 9 and validate required deployment/search capabilities.
- One customer-service supervisor and three specialists: financial, technical, and sales, including upsell and cross-sell.
- Chat and voice in the initial delivery, with shared identity and conversation continuity.
- Persistent memory using MongoDB Agent Engine's memory framework, taking mem0 as a conceptual reference.
- Prepare deployment to MongoDB Agent Engine; validate its runtime contract with OpenAI Agents SDK.
- Prefer MongoDB Auto Embedding wherever the required model/workflow is supported; document direct Voyage exceptions.
- Semantic cache with expiration, invalidation, tenant isolation, and protection against private or stale transactional data reuse.
- Keep Python 3.15 and use the official Voyage HTTP API for direct calls; preserve native Auto Embedding where supported ([ADR-0015](adr/0015-voyage-http-python315.md)).
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

Use MongoDB as the integrated operational/full-text/vector data platform to reduce separately operated engines and synchronization pipelines. Use the two existing clusters approved in [ADR-0017](adr/0017-two-cluster-memory-boundary.md): OpenAI-SDK for application data and ClusterDemoTelco for shared Engine memory; segregate environment/service-domain databases and service-owned collections with least-privilege identities. Enforce tenant/ACL isolation in shared collections. Align application configuration, backing services, stateless processes, releases, and administration with Twelve-Factor; do not claim that Twelve-Factor or namespace names provide isolation. Validate Engine attachment to its designated memory cluster and preserve managed namespaces.

The canonical project creation plan is `initial_plan.md` at the project root.

## Codex implementation foundation

Use root AGENTS.md, bounded task records, contribution/review guidance, and executable repository checks. Intended GitHub repository: https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk. Authored workflow files do not establish remote configuration or successful CI. Preserve remote work when access becomes available.

Include explicit typed function-calling examples for invoices, authorized ingestion jobs, and approved simulated plan changes. Evaluate semantic response quality with calibrated offline LLM judges and independent current references; online judge gating is optional, not an SDK-provided correctness guarantee.

## Accepted delivery decisions and current phase

MIT licensing and acceptance of the automated isolated handoff are recorded in
[ADR-0028](adr/0028-mit-automated-demo-handoff.md). The expanded semantic validation,
calibrated candidate cache and isolated evaluator are recorded in
[ADR-0027](adr/0027-bounded-knowledge-evaluation-cache.md) and
[EVAL-001](tasks/EVAL-001-QUALITY.md); these are bounded demo results.

There are nine phases, numbered 0–8. Phases 0–7 are published with passing CI.
[Phase 8](tasks/OPS-001-RESILIENCE.md) scalability/resilience is complete for the approved demo scope; manual publication is pending. User-performed commit/push
and a pause at each completed phase remain the delivery workflow.

## Decision lookup

| Requester decision | Authoritative record |
| --- | --- |
| Engine precedence; SDK orchestration | [ADR-0018](adr/0018-engine-feature-precedence.md) |
| Two existing Atlas clusters and domain ownership | [ADR-0017](adr/0017-two-cluster-memory-boundary.md) |
| Requester may approve their exact action; native 30-day retention/expurgo accepted without further proof | [ADR-0019](adr/0019-requester-approval-memory-retention.md) |
| Email/password, user/admin roles and admin-only registration | [ADR-0020](adr/0020-demo-email-password-auth.md) |
| Demo limited to semantic/episodic continuity | [ADR-0021](adr/0021-demo-semantic-episodic-continuity.md) |
| Private operator CLI identity allowed in demo backend | [ADR-0022](adr/0022-demo-private-engine-cli-identity.md) |
| Quiet-environment voice and bounded retries | [ADR-0023](adr/0023-quiet-environment-demo-voice.md) |
| Governed PDF approval/publication | [ADR-0026](adr/0026-governed-knowledge-publication.md) |
| Expanded semantic validation and calibrated candidate cache | [ADR-0027](adr/0027-bounded-knowledge-evaluation-cache.md), [EVAL-001](tasks/EVAL-001-QUALITY.md) |
| MIT and automated handoff accepted | [ADR-0028](adr/0028-mit-automated-demo-handoff.md) |

These links index decisions; policy details remain in their authoritative records.

Phase 8 budget and routing decisions are authoritative in [OPS-001](tasks/OPS-001-RESILIENCE.md): USD 30 total provider consumption supersedes USD 10; Engine preview is uncharged per requester; retain direct OpenAI model and MongoDB gateway knowledge paths. Load namespace selection is recorded in [ADR-0029](adr/0029-isolated-load-environment.md). The requester approved remote resource creation; the exact plan was applied and verified.

The requester clarified Phase 8 application tests use M20 and previous phases used M10. Current cluster-specific observations and the historical limitation are recorded in [OPS-001](tasks/OPS-001-RESILIENCE.md), including the separate Engine-memory tier. The requester authorized continuing the bounded phase without further questions; this does not turn unavailable billing or unexecuted profiles into accepted results.

Final Phase 8 scope: the requester explicitly excluded production-capacity and pricing proof and requested committing the work. [OPS-001](tasks/OPS-001-RESILIENCE.md) records the superseded billing gate and completed demo acceptance. Historical unknown costs and test limitations remain unchanged; manual publication is pending.

## Confirmed profile and multilingual scope — 2026-11-01

The requester selected display name, timezone, language, photo and self-service
password change. Portuguese (Brazil), English and Spanish must cover interface,
agent responses and audio. [ADR-0032](adr/0032-multilingual-profile.md) supersedes
English-only user-facing requirements; [I18N-001](tasks/I18N-001-MULTILINGUAL.md)
and UI-001 define phased tests. Source identifiers and developer documentation stay
English. Commit/push/PR and automatic merge per phase are authorized after gates;
pause and ask before actions affected by an unresolved material question.

The requester confirmed editable Control Plane configuration limited to application limits and retrieval-cache settings. Feature toggles remain read-only. Explicit Save/Apply affects subsequent operations, preserving in-flight configuration snapshots; no restart/deploy button is included. UI-001 owns validation and activation tests; existing admin authorization and Engine ownership remain in force.


## Working agreements and acceptance refinements — 2026-11-01

- Keep [AGENTS.md](../AGENTS.md) current as durable instructions change. Local changes within scope require no additional permission; Atlas mutations that could affect other projects require prior requester approval of the concrete change.
- Language changes must preserve the active conversation; [I18N-001](tasks/I18N-001-MULTILINGUAL.md) owns continuity and in-flight acceptance tests.
- The Tokenomics cost dashboard must show actual source-reported monetary values, not estimates or fixtures. Missing actual-cost access is an unresolved acceptance dependency, not a completed cost feature; [TOK-001](tasks/TOK-001-TOKENOMICS.md) owns source semantics and coverage.
- Validation reports must identify executed local/CI tests and explain failures, corrections and rerun outcomes, following the completion-report contract in AGENTS.md.
