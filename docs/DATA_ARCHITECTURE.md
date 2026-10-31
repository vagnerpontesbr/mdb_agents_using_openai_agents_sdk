# Atlas application and managed-memory boundaries

Status: two-cluster boundary and bounded identity-database/Engine-memory controls validated in Phase 0; remaining application schemas and service identities are planned. See [current evidence](compatibility/PHASE_0.md).

Phase 4 implementation now uses the approved knowledge/ingestion resources in
[RAG-001](tasks/RAG-001-KNOWLEDGE.md). Its bounded ingestion implementation uses
`jobs` and polymorphic `staged_artifacts` (original PDFs/results and per-tenant
admission counters), with no separate attempts/outbox collections. The planned
namespace table below is not a claim that every listed collection exists.

## Rationale

MongoDB is the integrated data platform for operational documents, full-text Search, Vector Search, and native hybrid retrieval. The asset does not require separate operational, text-search, and vector-database products. Indexing the relevant MongoDB collection data reduces application-managed replication pipelines, duplicate external stores, synchronization logic, and operational tooling.

“One engine” means one integrated application data platform, not one physical process, index, or consistency model. Search indexes have readiness/refresh lag and distinct resource requirements. Mutable prices, balances, eligibility, and governance require authoritative reads. LLM inference, parsing, Voyage, and Engine services still exist. No zero-lag synchronization, zero internal duplication, or automatic cost saving is promised.

## Approved two-cluster topology

Use the existing OpenAI-SDK cluster for application data and ClusterDemoTelco for shared project-managed Engine memory, as approved in [ADR-0017](adr/0017-two-cluster-memory-boundary.md). Separate namespaces by environment and service/domain ownership. Application eval/load databases use OpenAI-SDK with separate credentials; schedule disruptive tests away from demonstrations. Logical isolation cannot isolate shared CPU, I/O, storage, failures, or administrative privileges.

Use deployment-allowlisted names such as `telecom_<env>_<domain>`, never arbitrary LLM/request-supplied database names. Proposed application namespaces:

| Database | Owner | Collections / access |
|---|---|---|
| `telecom_identity` | Implemented demo identity backend | `users`, `sessions`, `login_attempts`; restricted application credential, separate from Engine memory |
| `telecom_demo_runtime` | Planned application runtime | Domain idempotency records if needed; Engine owns run/review state. No app approval or transcript store under ADR-0018/0021 |
| `telecom_demo_knowledge` | Knowledge service | `documents`, `document_versions`, `chunks`, `review_events`, `retrieval_cache`, `outbox` |
| `telecom_demo_ingestion` | Ingestion service/workers | `jobs`, `attempts`, `staged_artifacts`, `outbox`; publication through the knowledge contract, no direct knowledge writes |
| `telecom_demo_business` | Simulated business adapter | `customers`, `accounts`, `invoices`, `plans`, `service_incidents`, `tickets`, `action_receipts` |
| `telecom_eval_*`, `telecom_load_*` | Evaluation/load identities | Copies of required service namespaces; negative-control data inaccessible to demo credentials |
| Engine-managed namespaces | Official Engine services | On ClusterDemoTelco: discover supported names/permissions and verify managed attachment; do not assume arbitrary renaming |
| Auto Embedding internal namespaces | MongoDB-managed functionality | Preserve internal ownership; no application writes or invented layout |

The implemented identity backend accesses only its identity collections; the future API/BFF needs no general cross-domain database access. Give each service a separate least-privilege identity; explicitly review any exceptional read grants. Use separate migration/index-management identities as services are implemented. The bounded identity demo currently grants CREATE_INDEX only on its three collections. The new Phase 1 API performs no startup index writes and exposes a separate idempotent administration command under [ADR-0024](adr/0024-phase-one-application-boundaries.md); the existing grants have not been changed; its exact grants and live denials are recorded in [COMP-005](tasks/COMP-005-DEMO-AUTH.md#restricted-application-identity-passes). The business adapter may begin as a module using its own credentials; process extraction follows measured needs. Collections reflect access patterns, lifecycle, and security, not one collection per customer, agent, intent, or day. Avoid unbounded transcript/chunk arrays.

Keep lexical/vector indexes on the same authorized source collection for native rank fusion, such as knowledge chunks or business plans. Native fusion is not cross-database federation. Cross-domain access uses service/adapter contracts; intentional read models require ownership, lineage, and refresh rules.

## Enforced isolation

- Database/collection roles restrict service access. Naming conventions alone provide no security.
- In shared collections, authenticated tenant/customer/ACL filters enforce application tenancy across CRUD, search, cache, and exports. MongoDB roles do not automatically filter documents by tenant.
- Compromised service credentials expose their granted scope; shared-collection tenancy is not physical or per-tenant credential isolation.
- Validate schemas and tenant-scoped identifiers/idempotency. Use TLS, secrets management, network restrictions, and role audits. No application `readWriteAnyDatabase` grants.
- Validate database configuration at startup; keep one bounded client pool per service process where appropriate and measure aggregate connections across replicas.
- Retention/TTL follows collection lifecycle. Business expiry is checked on reads; TTL deletion is not immediate authorization enforcement.
- Shared backup/restore and administrative access require operational procedures; do not assume independent database restore without validating tooling.

## Twelve-Factor alignment

Twelve-Factor governs application delivery and processes; it does not prescribe database-per-service or guarantee data isolation. Combine it with MongoDB authorization and access-pattern modeling.

| Factor | Application |
|---|---|
| Codebase | Versioned monorepo with explicit service boundaries and independently releasable artifacts |
| Dependencies | Explicit uv/frontend dependencies and locks |
| Config | Inject per-service URI, database names, credentials, quotas, and models; no secrets in code/logs |
| Backing services | Attach Atlas, Engine, and providers through configuration and documented contracts |
| Build, release, run | Immutable artifacts, versioned configuration releases, separate execution |
| Processes | Stateless replicas; durable state in owned backing services |
| Port binding | Explicit endpoints and authenticated internal contracts |
| Concurrency | Scale process types independently within shared Atlas/provider limits |
| Disposability | Fast startup, graceful shutdown, leased work, safe retries |
| Dev/prod parity | Same contracts/migrations with declared differences; mocks do not prove provider semantics |
| Logs | Structured, redacted event streams collected externally |
| Admin processes | Versioned one-off migration, seed, reindex, and provisioning jobs with dedicated privileges |

## Acceptance

Verify application data targets OpenAI-SDK and project-managed Engine memory targets ClusterDemoTelco. Validate each connection independently; topology approval does not resolve Engine service failures. Test allowed and denied access per identity, forbidden demo-to-eval access, tenant filtering, migration permissions, and operational-to-search visibility lag. Measure shared contention during bounded load; stop on isolation violations.

References: [MongoDB research](research/mongodb-engine.md), [MongoDB collection guidance](https://www.mongodb.com/docs/manual/data-modeling/design-antipatterns/reduce-collections/), [Twelve-Factor](https://12factor.net/).

## Phase 8 isolated load resources

[ADR-0029](adr/0029-isolated-load-environment.md) defines explicit load-only
constructor selection. [The resource plan](../compatibility/phase8-resource-plan.json)
defines `telecom_load_ingestion` and `telecom_load_knowledge` on OpenAI-SDK,
with four scoped identities and existing schema/index definitions. The requester approved the plan, and both namespaces and the four scoped roles/users
were created. Strict validators, 208 role controls and index readiness passed.
Demo defaults and the Engine memory cluster remain unchanged; logical isolation
does not establish physical resource isolation.
