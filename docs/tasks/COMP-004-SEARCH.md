# COMP-004-SEARCH: Native filtered search compatibility proof

- Status: Done for the bounded synthetic probe; parent COMP-004 remains in progress
- Owner: Repository maintainer
- Dependencies: Existing Atlas 9.0.4 cluster, explicit index approval
- Relevant ADRs: [ADR-0004](../adr/0004-embedding-retrieval.md), [ADR-0011](../adr/0011-single-cluster-logical-isolation.md)

## Scope

Create the two approved indexes on four synthetic documents in `telecom_eval_knowledge.phase0_search_probe` on the existing cluster. Prove lexical search, Auto Embedding text queries and native `$rankFusion` with tenant/ACL/publication filters inside both branches.

## Acceptance criteria

- Both indexes become READY and queryable with the approved definitions.
- Unfiltered lexical and vector controls return all four synthetic records.
- Filtered lexical, vector and hybrid queries return only `phase0_allowed`.
- Execute no more than six live queries, preserve 512 dimensions and do not modify Engine/internal namespaces.

## Validation plan

Use the [approved plan](../../compatibility/search-probe-plan.json) and [exact pipelines](../../compatibility/search-probe-pipelines.json). Confirm index definitions and readiness via MCP. Distinguish native filtering from database roles and from end-to-end backend authorization.

## Evidence and handoff

All bounded acceptance criteria passed on 2026-10-28 with five live queries. See the [machine-readable evidence](../../compatibility/search-probe-evidence.json) and [Phase 0 checkpoint](../compatibility/PHASE_0.md#live-search-checkpoint). The cluster now contains the four synthetic documents and two indexes; no cleanup was performed. Documentation and query fixtures are locally authored, not committed or pushed. This does not complete Phase 0 or establish RAG quality, full governance, service-role isolation or Engine compatibility.
