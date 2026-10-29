# COMP-004-SEARCH: Native filtered search compatibility proof

- Status: Done for the bounded synthetic probe; parent COMP-004 remains in progress
- Owner: Repository maintainer
- Dependencies: Existing Atlas 9.0.4 cluster, explicit index approval
- Relevant ADRs: [ADR-0004](../adr/0004-embedding-retrieval.md), [ADR-0015](../adr/0015-voyage-http-python315.md), [ADR-0017](../adr/0017-two-cluster-memory-boundary.md)

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

## Model coverage follow-up (2026-10-29)

Read-only MCP inspection confirmed both indexes remain READY and queryable on the application cluster. The sixth bounded query used `model: "voyage-4"` with `query: {"text": "optical cable"}` against the existing `voyage-4-lite` index at 512 dimensions. It returned only `phase0_allowed` with tenant, ACL and publication prefilters. See the [exact pipeline and result](../../compatibility/search-model-coverage-evidence.json). No indexes, documents or Engine-managed namespaces were changed.

| Requested path | Verified evidence | Remaining scope |
| --- | --- | --- |
| `voyage-4-lite` Auto Embedding | Document indexing and text-query retrieval at 512 dimensions; filtered lexical/vector/native rank fusion | Application integration and measured retrieval quality |
| `voyage-4` Auto Embedding | Query model override against the existing lite index at 512 dimensions | Document indexing with this model and production model selection are not tested |
| `voyage-context-4` direct HTTP | Existing Atlas HTTP probe passed contextual documents with auto-chunking and query embeddings at 256 dimensions | Contextual vector ingestion, dimension selection and end-to-end retrieval remain untested |
| `rerank-3` | Existing Atlas HTTP contract probe passed | Retrieval-to-rerank application integration and quality measurement remain untested |
| `rerank-3-lite` | No live evidence recorded | Economy-model option remains untested |

The prior contextual/reranking result is recorded in the ignored local artifact `artifacts/compatibility/voyage-atlas-http.json`, summarized in the Phase 0 checkpoint. It proves provider HTTP contracts, not Python network transport or retrieval quality. General embedding transport tests are due when those application paths are implemented, per ADR-0015; optional model comparisons do not invalidate this completed bounded search task.

MongoDB documents the [Voyage 4 shared embedding space](https://www.mongodb.com/company/blog/technical/moe-shared-embedding-spaces-how-voyage-4-scales-smarter) and [Auto Embedding model support](https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/models/). Shared model space does not establish application quality. The plain-string `query` form remains untested; this evidence uses the MCP-supported object form above.
