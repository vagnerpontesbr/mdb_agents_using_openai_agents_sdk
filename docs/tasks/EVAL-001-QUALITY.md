# EVAL-001: Quality, repetition and governed cache

Dated checkpoints below preserve historical results and pending work at that time.
[Publication status](../runbooks/REPOSITORY_SETUP.md) and [RUN-001](RUN-001-RUNTIME.md)
identify the current published checkpoint and active runtime.

- Status: Completed for the approved bounded demo; final workflow 8 acceptance passed; published as `1a81be6` with passing CI
- Owner: Telecom demo maintainer
- Dependencies: RAG-001, MEM-001, scoped Atlas resources and provider access
- Relevant ADRs: [ADR-0006](../adr/0006-evaluation-truth.md), [ADR-0009](../adr/0009-deterministic-responses.md), [ADR-0018](../adr/0018-engine-feature-precedence.md)

## Current checkpoint: 2026-10-31

Calibration v3 passed its frozen criteria in both new validation groups. The
[assessment](../../compatibility/phase5-calibration-v3-assessment.json) records a
selected threshold of 0.91, 5/6 new paraphrases reused, 14/14 effective top-one source
matches and no relevant-source loss. Unrelated billing/Wi-Fi questions fell back
to fresh search. The deployed workflow 8 uses 0.91; build and deployment succeeded. The final
eight-run journey verification passed with native runtime cleanup. Duplicate cached references now fall
back to fresh governed retrieval. Final local checks: 128 backend tests, 86 hosted
contracts, Ruff and mypy passed; real cache validity/invalidation checks passed in
[final cache evidence](../../compatibility/phase5-cache-final-evidence.json).

Earlier sections below retain the chronological evidence, including failed 0.99 and
0.98 experiments. Their “open” and “not passed” statements describe those earlier
checkpoints and are superseded by this current status. They must not be removed or
represented as successful experiments. The bounded demo does not establish general
RAG accuracy, load capacity, dollar cost or tool-argument accuracy where traces redact
arguments. Phase 6 is not authorized.

## Scope

Phase 5 includes repeated-run evaluation, stale-reference/current-truth experiments,
Matryoshka dimension comparison and a governed semantic retrieval cache. The implementation includes scoring, an opt-in Engine runner, an isolated corpus,
an offline judge and a bounded candidate cache. Phase 5 is complete for the bounded demo; the limits below remain explicit.

The [versioned dataset](../../examples/telecom/evaluation/journey-v1.json) covers
invoice, sales, mixed and technical requests. Its labels are developer-authored
synthetic regression expectations, not independent SME annotations. Exact text is
useful for protected templates and exact-source regression, but is not semantic
correctness or proof that a citation is currently eligible.

## Acceptance criteria

- Report execution/contract validity, routing, parameter accuracy, outcomes,
  independent factual correctness and exact wording separately, with denominators.
- Report missing evidence as unavailable. Keep failures and unattempted runs visible.
- Preserve Engine as primary trace owner. Portable reports retain execution/session
  IDs and response hashes, not raw responses, user identities or credentials.
- Compare 256/1024-dimensional contextual retrieval on the same independently labeled
  dataset; measure actual provider outputs, never assume slicing is supported.
- Run isolated obsolete-source, governed abstention and valid replacement cases.
  Distinguish stale-label relevance, faithfulness and current business correctness.
- Cache only governed candidate source references. Tenant/ACL, checksum, current
  version, expiry/review and policy checks must pass again on every read. Similarity
  is not authorization. Exercise concurrent invalidation and scope denials.
- Calibrate an offline LLM judge against independently reviewed labels, retaining
  disagreements and grader errors. Do not use judge scores to authorize actions.

## Validation plan

Use the [runbook](../runbooks/PHASE_5.md). Local metric tests run in existing CI.
The live runner allows at most three repetitions per case (12 invocations total),
stops at its first unavailable final contract, and never retries an invoke. Existing
native execution budgets remain active. Fresh sessions retain Engine memory, so
runs are not independent samples. No cache, index, policy or deployment changes
are made by this runner.

## Evidence and handoff

Phase 4 commit `1a52afce2815be3530d77cb7a714001f412ad206` is on the remote branch;
both jobs passed in [CI run 41062532149](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41062532149).

Current deterministic checks: 125 backend tests and 86 hosted contract tests passed;
Ruff passed and mypy passed for 27 source files on 2026-10-30.

The approved [resource proposal](../../compatibility/phase5-resource-proposal.json)
was applied on OpenAI-SDK: two collections, four READY search indexes, three classic
indexes and two collection-scoped identities. [Resource evidence](../../compatibility/phase5-resource-evidence.json)
records 56 role checks and four valid/invalid schema probes. The evaluation URI stays
local; only the cache URI was added to the hosted workspace. Shared tools and Engine
memory resources are unchanged.

The cache build `bld_01M66Z3MM27JSMXDR441FMCJ6Q` deployed successfully as
`deploy-54f31999`, workflow version 7. Read-only health verification on 2026-10-30
reported four ready agent replicas; this does not prove invoke capacity.
[Cache evidence](../../compatibility/phase5-cache-evidence.json) proves real cold/warm
retrieval, matching cited answers, scope denial, expiry and changed-provenance fallback.
No published source was modified. Cache slots are globally bounded to 128 and expire
logically within 15 minutes; source validity can shorten that interval.

[Corpus evidence](../../compatibility/phase5-corpus-evidence.json) uses four synthetic
PDFs extracted by real Docling, actual provider 256/1024-dimensional embeddings,
native hybrid fusion and reranking. Each dimension returned the expected top result
for six queries. The obsolete-label negative control scored perfectly against stale
labels and zero against current labels; missing replacement abstained. This small
experiment does not establish general RAG quality, storage savings or generated-answer
correctness. Production remains 1024 dimensions.

[Judge evidence](../../compatibility/phase5-judge-evidence.json) records six real
Responses calls with agreement on both faithfulness and current-reference labels.
The requester subsequently approved the summarized demo reference and linked six
examples on 2026-10-30. The dataset records that review; the original report retains
its at-run pending-review status and hash. This is demo owner review, not external
SME validation. The judge has no tools or authorization authority.

All failed hosted attempts are retained. The [deployed-cache baseline](../../compatibility/phase5-journey-cache-deployment.json)
completed two invoice and two sales runs with valid contracts, expected routing and
exact reference matches, then stopped on the mixed case with HTTP 503
`POOL_EXHAUSTED`; three planned invocations were not attempted. Fifteen-second
spacing did not prevent this. Do not report an eight-run pass.
[Native session metrics](../../compatibility/phase5-native-session-metrics.json)
contain the expected tool selection and token counts for four successful sessions.
The API returned null root execution IDs, so attribution is explicitly session-only.
The original zero-row trace report is superseded by this corrected collection.
Tool arguments are redacted: parameter accuracy remains unavailable, not inferred
from final answers. Dollar cost remains unavailable.

## Documentation findings and open gates

The Engine documentation index, SDK base API and trace documentation were inspected.
They establish native tracing; they do not establish a native semantic-answer-cache
or dataset/judge API usable by this adapter. This is an evidence gap, not a claim
that those capabilities cannot exist. The proposed domain retrieval cache is not a
memory or trace store. No alternate Engine memory/review/replay owner is introduced.

Official OpenAI evaluation guidance requires task-specific metrics and calibration
against human labels. Its current documentation announces Evals platform read-only
access on October 31, 2026 and shutdown on November 30, 2026. Do not build this asset
on that retiring hosted service; any future offline judge should use the supported
model invocation boundary and preserve Engine precedence where applicable.

Remaining: improve and validate semantic admission/source recall before accepting
semantic reuse; retain unavailable parameter metrics as an explicit limitation. Native
capacity recovery and generated-answer experiments are now recorded below. Phase 6 is
not authorized. See [ADR-0027](../adr/0027-bounded-knowledge-evaluation-cache.md).

Sources read on 2026-10-30:

- [Engine documentation index](https://www.mongodb.com/docs/agentengine/llms.txt)
- [Engine trace documentation](https://www.mongodb.com/docs/agentengine/manage/inspect-traces/)
- [Engine base SDK API](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk/docs/api/)
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

## Follow-up diagnostics and generated answers

The failed mixed request was recovered by native session lookup as an execution
with terminal `error` and `POOL_EXHAUSTED`; see
[recovery evidence](../../compatibility/phase5-capacity-recovery-evidence.json).
No request was resubmitted. Official runtime-session documentation distinguishes
reserved sandbox capacity from durable conversations. The evaluator now requests
native release only after checking its own session and completed execution, then
waits at most 40 seconds for release. It stops if release cannot be confirmed.
Four new deterministic cases cover active/foreign session refusal and delayed release.

The [generated-answer experiment](../../compatibility/phase5-answer-experiment.json)
contains three real generations and three grades. The stale-source answer was
faithful but operationally wrong. With no eligible source, the model escalated;
the strict current-action grader still marked it incomplete. With the current
source, the model incorrectly changed “link the ticket” to “link the device,” and
the judge flagged both fidelity and current correctness. These are retained findings,
not passing scores. The deployed knowledge tool returns exact cited source excerpts;
this offline free-generation experiment does not change that behavior. It also shows
why a valid response schema or current source alone cannot guarantee correctness.

Sources: [list runtime sessions](https://www.mongodb.com/docs/api/doc/agentengine/operation/operation-get-api-v1-projects-parameter-workspaces-parameter-runtime-sessions)
and [stop runtime session](https://www.mongodb.com/docs/api/doc/agentengine/operation/operation-post-api-v1-projects-parameter-workspaces-parameter-runtime-sessions-parameter-stop).
Native release preserves messages, execution records and durable conversation history.

## Semantic threshold finding

[Similarity evidence](../../compatibility/phase5-similarity-evidence.json) screens
seven actual contextual query embeddings (six comparisons). The 0.99 threshold
admitted a different-product query (score 0.99153) and rejected an equivalent
paraphrase (0.98710). Scope filters remain mandatory and reject changed product
metadata, but this small screen cannot establish semantic cache quality. No threshold
was tuned to this sample. The requester chose broader semantic validation on 2026-10-30; Phase 5
remains open. The expanded dataset freezes 48 equivalence comparisons in four
topical groups plus 24 scope-denial checks before provider execution. Existing experimental hosted behavior has not been silently relabeled
as calibrated or changed by this offline screen.

## Completed hosted baseline with native cleanup

[The complete baseline](../../compatibility/phase5-journey-runtime-release.json)
passed eight of eight invocations: two each for invoice, sales, mixed and knowledge.
Each returned valid final contracts, expected routing, completed outcomes and exact
reference matches. Every completed evaluation session was released natively before
continuation. The prior four-success/POOL_EXHAUSTED reports remain unchanged.
This supports the bounded sequential demo; it does not measure concurrent capacity.
No shared deployment scaling, memory deletion or application runtime policy change
was needed. Native usage collection is in
[the trace report](../../compatibility/phase5-runtime-release-trace-metrics.json).

## Expanded semantic validation results

The requester selected broader validation. The frozen
[48-case dataset](../../examples/telecom/evaluation/semantic-cache-v2.json) covers
provisioning, optical alarms, billing and Wi-Fi. Actual results are retained in
[expanded live evidence](../../compatibility/phase5-semantic-expanded-live.json).
The existing cosine/1024 cache index was independently confirmed READY through the
MCP admin connection. The runtime identity correctly denied index inspection in
[the initial preflight](../../compatibility/phase5-semantic-expanded.json); its role
was not broadened. Twelve bounded real embedding calls were used for the final run.

| Partition | Equivalent / different queries | True / false hits | Missed equivalents | Precision | Equivalent recall |
| --- | --- | --- | --- | --- | --- |
| Development | 8 / 16 | 2 / 1 | 6 | 66.7% | 25% |
| Held out | 8 / 16 | 2 / 0 | 6 | 100% | 25% |
| Combined | 16 / 32 | 4 / 1 | 12 | 80% | 25% |

All four true hits were identical queries. None of twelve equivalent paraphrases
was admitted at 0.99. The false admission changed FiberBox X1 to X2 in the question
while preserving the supplied scope. This reproduces the earlier similarity concern
through the actual MongoDB index and production cache lookup, not cosine arithmetic
alone. Twenty-four explicitly supplied tenant/ACL/product/firmware/region/language
changes were denied. Text mentioning another product does not itself change trusted
scope; these checks must not be conflated.

Four temporary synthetic references used an isolated random tenant and vacant fixed
slots. All were removed; cleanup was verified. No published source, application
role, Engine memory, deployed code or similarity threshold changed in this expansion.
The reference resolver is synthetic, so these figures measure admission against
query-equivalence labels, not factual answer quality or downstream source recall.
A non-equivalent question could still share relevant candidates; source-recall
validation must measure that separately. No capacity or statistical generalization
claim follows from 48 developer-authored cases.

**Quality gate: not passed.** The current threshold demonstrates neither useful
paraphrase reuse nor zero false admission. Do not raise/lower it from this same
sample and declare success. The next bounded deliverable is a relevance-labeled
multi-source corpus comparing warm cached candidates with fresh governed retrieval,
including text/scope disagreement, followed by an untouched validation partition.
Do not add an intent classifier or let a judge grant authorization. Phase 5 remains
open; no further requester decision is required to continue this chosen validation.

Checks for this increment: 121 backend tests passed, including metric-denominator
and partition-separation tests; Ruff and repository checks passed. Hosted runtime
code was unchanged, so the earlier 86 hosted contract tests and eight-run hosted
baseline remain the relevant deployed evidence.

## Source recall comparison: actual cached candidates versus fresh search

[Source recall evidence](../../compatibility/phase5-source-recall-evidence.json)
uses a frozen [32-source corpus](../../examples/telecom/evaluation/cache-source-recall-v1.json),
exceeding the 20-candidate cache limit. Twelve questions cover identical requests,
paraphrases, another question using the same source, and product/alarm changes.
Both partitions were fixed before provider calls. Real contextual embeddings,
MongoDB hybrid fusion, the production cache lookup and current-query reranking were
used. All temporary source/cache rows were removed and absence verified.

- Fresh retrieval ranked the labeled source first in 12/12 cases.
- Effective retrieval (warm on hits, fresh on misses) ranked it first in 12/12 cases.
- Three actual cache hits occurred: two identical questions and one product change.
- None of those three hits lost the relevant source from its candidate set.
- The product-change hit contained the new product's required source and reranking
  selected it first. The earlier query-equivalence false admission was therefore
  not a source-recall failure in this measured corpus.
- Both paraphrases and both same-source/different-question cases missed the cache.
- Top-three lists included sources outside the single-source relevance label; top-one
  success is not evidence that every returned source is applicable.

This narrows the earlier gate finding: query equivalence is a diagnostic, while the
cache stores candidate sets, not answers. Different questions may safely share
candidates only when authoritative eligibility and current-question relevance are
preserved. This test does not prove that condition for arbitrary corpora. It uses
synthetic applicability labels and a broad supplied demo scope; it is not a native
publication test, equipment parser or final generated-answer evaluation.

Calls actually made: 16 document embedding requests (real 256 and 1024 dimensions
required by the evaluation schema), three query embedding requests and 15 reranks.
No production threshold, cache implementation, index, role or hosted build changed.
Checks: 123 backend tests, Ruff, repository validation and diff whitespace passed.

Phase 5 remains open for useful semantic reuse: candidate preservation passed this
bounded corpus, but paraphrase hit rate remains poor. Future admission calibration
must optimize relevant-source preservation and useful reuse separately, using a
new untouched validation set; it must not tune on the held-out results above and
relabel them as independent validation. The historical reports remain unchanged.

## Atlas resumption and threshold calibration

On 2026-10-31 the requester confirmed both Atlas clusters had resumed. Read-only MCP
inspection verified the cache index and three evaluation indexes READY/queryable.
The [v2 calibration dataset](../../examples/telecom/evaluation/cache-source-calibration-v2.json)
fixes eight development cases, eight new held-out questions and threshold candidates
before invocation. Query overlap with previous validation datasets is tested.
The selection rule requires at least 50% development paraphrase reuse, no loss of
relevant candidates or top-one correctness, and correct effective top-one sources
for all development cases. Selection rejects any held-out rows.

The development-only selection chose 0.98: two of three paraphrases reused the
candidate cache versus zero at 0.99, with eight of eight effective top-one matches
and no source recall regression. The selected value was saved before held-out
retrieval/reranking observations. This is not yet a deployed threshold change;
validation evidence determines whether the candidate qualifies for the bounded demo.

The [complete calibration evidence](../../compatibility/phase5-calibration-evidence.json)
and [assessment](../../compatibility/phase5-calibration-assessment.json) show that 0.98
**failed the new validation reuse criterion**: zero of three paraphrases hit, and
only the identical question reused the cache (1/8 hits, the same as the 0.99 baseline).
All eight effective validation top-one sources were correct and there was no measured
loss of candidate recall. No selected-threshold production deployment was performed.
The 16-case experiment used 16 document embedding calls, four query embedding calls
and 32 reranks; cleanup was verified. It is a negative calibration result, not a
provider outage or a successful quality gate. The selected threshold was not adjusted
after observing held-out performance.

Checks: 125 backend tests passed, including held-out leakage rejection, source-loss
rejection, and query non-overlap; Ruff and repository checks passed. No new Engine
probe was necessary: this step depends on Atlas/cache/provider boundaries only.
Phase 5 remains open. Further development coverage must account for variation in
phrasing before another frozen evaluation; do not repeatedly tune to this validation
partition and claim independent generalization. The user has already authorized
expanded semantic validation; no new authorization decision is pending.

## Final calibration and deployment record

The [v3 experiment](../../compatibility/phase5-calibration-v3-evidence.json) used
40 synthetic sources and 34 comparisons. Old v2 validation was explicitly promoted
to development; new held-out queries are disjoint from prior experiments. The
highest threshold meeting at least 50% paraphrase reuse in EACH development group,
without candidate-recall or top-one loss, was frozen at 0.91 before new validation.
The new groups achieved 2/3 and 3/3 paraphrase hits respectively, with all 14 top-one
labels correct. Four unrelated billing/Wi-Fi queries missed the cache as intended.
Cleanup of all temporary evaluation/cache rows was verified.

The deployed threshold is a bounded-demo decision, not a probability or universal
safety guarantee. Exact source release, current governance, ACL/applicability checks,
reranking, bounded slot count and logical expiration remain mandatory. The primary
trace/memory/review owners remain native Engine services. The candidate cache stores
no raw queries or generated answers.

The [source manifest](../../compatibility/phase5-final-source-manifest.json) hashes
the allowlisted staged source and configuration. Staging is outside Git; runtime
publication must not be confused with committing/pushing the local Phase 5 changes.

The final runtime was built as `bld_01M691YPABN60FEKHW6E1KZGB5` and deployed as
`deploy-af009ed4` on 2026-10-31. [Deployment evidence](../../compatibility/phase5-final-deployment-evidence.json)
records successful rollout and healthy OE/memory/agent/tool components. A healthy
deployment does not replace the final invoke-path acceptance. No Git commit or push
was performed by the assistant.

## Phase 5 completion: 2026-10-31

[Final hosted evidence](../../compatibility/phase5-journey-final-evidence.json) passed
8/8 invocations on the final deployed workflow: two each for invoice, sales, mixed
and knowledge. All returned valid contracts, expected routing, completed outcomes
and exact reference matches. All eight runtime reservations were released natively.
[Final native metrics](../../compatibility/phase5-final-trace-metrics.json) preserve
Engine as trace owner; session correlation and redacted-argument limitations remain.
The source manifest binds the deployed build to the reviewed local source snapshot.

Bounded acceptance is complete: scoped resources, independent reference provenance,
source/current-truth separation, actual 256/1024 embeddings, cache invalidation,
calibrated useful semantic reuse, hosted repetition, tests and documentation.
The final deterministic checks passed: 128 backend tests, 86 hosted contract tests,
Ruff, mypy (27 source files), repository links/ADRs and whitespace validation.

Remaining limitations are not hidden phase failures: labels and corpus are synthetic,
review is demo-owner review rather than an external SME study, source top-one
metrics do not guarantee every top-three citation or generated answer is correct,
load/capacity and dollar costs are not measured, and redacted tool arguments cannot
be graded. These boundaries are explicit in each evidence report. Phase 8 load and
resilience work has not started.

Git publication is the user's next manual action. HEAD remains Phase 4 `1a52afc`;
Phase 5 code and documentation are locally modified/untracked, while workflow 8 is
already deployed and remotely verified. No Phase 5 CI success is claimed before
commit/push. Stop at this phase boundary and wait for the user's confirmation.
