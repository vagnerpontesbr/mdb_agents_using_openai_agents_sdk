# ADR-0017: Separate application and shared Engine memory clusters

Current acceptance is recorded in the [Phase 0 checkpoint](../compatibility/PHASE_0.md). Earlier evidence below preserves historical observations; superseded blockers do not reopen accepted demo gates.

- Status: Approved by user; bounded memory/application role controls passed in Phase 0
- Date: 2026-10-28
- Owner: Repository implementation
- Supersedes: [ADR-0011](0011-single-cluster-logical-isolation.md)
- Specification: [data architecture](../DATA_ARCHITECTURE.md)

## Context

The existing Engine project shares managed memory with geo-intelligence-network on ClusterDemoTelco. The application uses OpenAI-SDK. The user explicitly approved this two-cluster topology and selected a dedicated agentsdk workspace within the same Engine project.

## Decision

Use the existing OpenAI-SDK cluster for application, knowledge, ingestion, business and logically isolated application eval/load data. Retain project-managed memory on the existing ClusterDemoTelco cluster. Do not create another cluster or copy managed memory into application collections. Preserve service-owned collections, least-privilege identities and independent tenant/ACL enforcement on both sides.

The agentsdk workspace stores the application connection as APP_MONGODB_URI. The project's existing MONGODB_URI remains the managed-memory connection. The application accesses managed memory through the official Engine API; it does not gain a competing direct memory writer. Memory remains shared by Engine project, not isolated by workspace registration.

## Alternatives considered

Move all data onto one cluster, or move agentsdk to a new Engine project with separate memory. The user selected retaining the existing shared memory and separating only the workspace.

## Consequences and tradeoffs

Application and memory have separate network, credential, connection, backup and failure boundaries. Cross-cluster transactions or native search fusion are not assumed. Memory operations can still fail when application Atlas access succeeds. Shared Engine project changes can affect geo-intelligence-network. Coordinate recovery, deletion and load tests across these boundaries.

## Validation before implementation acceptance

Verify each connection targets its intended cluster and has the required permitted/denied operations. Prove real Engine record/context continuity, tenant isolation and deletion independently of application CRUD/search. Test failure behavior when either backing service is unavailable. The earlier HTTP 500 and bounded STM/durable retrieval blockers were resolved in the [Phase 0 evidence](../compatibility/PHASE_0.md). Authorization and remaining lifecycle acceptance are still pending; topology approval alone is not provider acceptance.

## Revisit trigger

Revisit for memory isolation, operational ownership, residency, recovery or cost requirements that cannot be met by the shared Engine project.
