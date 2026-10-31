# Phase 5: Evaluation and cache

Historical phase-specific evidence and versions follow. Use [Phase 7](PHASE_7.md)
for the active runtime and [publication status](REPOSITORY_SETUP.md) for current Git/CI.

The authoritative status and limits are in [EVAL-001](../tasks/EVAL-001-QUALITY.md).
The approved Atlas resources and hosted candidate cache are applied. Phase 5 bounded
acceptance is complete: calibration v3 passed at 0.91, and all eight final hosted
journeys passed on workflow 8. Git publication is pending. Earlier failed reports
are preserved. Native evaluator cleanup releases runtime capacity without deleting
conversation or execution history.

## Deterministic evaluation checks

```sh
uv run --frozen pytest -q tests/foundation/test_evaluation.py
uv run --frozen ruff check src/telecom_app tests/foundation
uv run --frozen mypy
uv run --frozen python scripts/run_phase5_evaluation.py --output /tmp/evaluation-unused.json
```

Without `--allow-live` the command validates the synthetic dataset, reports its
planned invocation count and exits without reading credentials or creating output.
Failures remain in metric denominators. Metrics without a trace/reference are null,
not successful zeros or fabricated measurements. Pair agreement is undefined with
fewer than two observed responses. Binary ranking metrics penalize missing results
in Precision@k and reject duplicate result IDs.

## Bounded hosted baseline

With the existing private CLI session and scoped reader URI injected:

```sh
uv run --frozen --env-file .env python scripts/run_phase5_evaluation.py \
  --allow-live --repeats 3 --output /tmp/evaluation-new.json
```

Choose a fresh output path; an existing file is never overwritten. The runner
reserves the report before paid calls and updates it after every attempt. It calls
four fixed, read-only questions as the registered synthetic owner, using a new
session for every run. It is an operator probe, not a login test. At most twelve
sequential invokes are admitted. Model/tool fan-out is constrained by the existing
Engine budgets; the report does not invent token usage or dollar cost.

On an admission/contract error it stops and records the opaque session ID. Inspect
that native session before any deliberate new run; do not resubmit uncertain
requests automatically. No raw responses or native trace payloads are exported.
The pinned knowledge reference intentionally fails exact-match regression when the
published source changes; review and version the dataset rather than deriving new
expected answers from the response under test.

## Applied Atlas resource scope

Review [phase5-resource-proposal.json](../../compatibility/phase5-resource-proposal.json).
Regenerate offline with a new path:

```sh
python3 scripts/prepare_phase5_resources.py --output /tmp/phase5-resources-review.json
```

| Resource | Approved scope |
| --- | --- |
| Knowledge cache | New `telecom_demo_knowledge.retrieval_cache`, candidate references only; at most 128 entries and at most 15-minute logical lifetime |
| Isolated corpus | New `telecom_eval_knowledge.phase5_chunks`, at most 200 synthetic chunks; old Phase 0 probe unchanged |
| Search indexes | Cache context-4/1024; evaluation lexical, context-4/256 and context-4/1024 |
| Classic indexes | Cache expiry TTL, cache scope/creation, unique evaluation dataset/version/chunk |
| Credentials | Two new roles/users, each CRUD-scoped to only its new collection and only OpenAI-SDK |
| Workspace | One new `KNOWLEDGE_CACHE_URI` binding, only after domain acceptance; evaluation credential stays local |

The JSON contains exact names, index definitions, strict/error validators and
privileges. Existing documents/roles/indexes are not to be modified. No memory,
shared policies, tool names or ClusterDemoTelco resources change. Runtime identities
cannot create indexes, grant roles or read the identity database. A drift check
must precede application. Definition changes need another review.

Cache entries store bounded source references and a query embedding/hash; the
original query and final generated answer are not stored. Authoritative source
revalidation remains mandatory and TTL cleanup is asynchronous. Cache failures
must fall back to the existing governed retrieval path, not bypass its checks.
Dimensions must be produced by the documented provider contract; approval of an
index is not proof of model compatibility or quality.

## Read-only metrics and review

Collect native session metrics without exporting raw traces:

```sh
uv run --frozen python scripts/collect_phase5_trace_metrics.py \
  --report compatibility/phase5-journey-cache-deployment.json \
  --output /tmp/phase5-session-metrics-new.json
```

Choose a fresh output. Null root execution IDs mean session correlation only.
Redacted tool parameters cannot be graded. Preserve failed invoke reports and
inspect their native sessions before considering a new run. HTTP 503 can still
have an associated execution; never infer nonexecution from the HTTP response.
The baseline supports `--pause-seconds 30`, but spacing is not a capacity fix.

The synthetic reference has requester approval for this demo. Original judge
results retain the dataset hash and review status at execution time; do not rewrite
historical evidence to imply approval existed earlier. The historical 0.99 threshold was experimental. Current bounded-demo calibration
and its limits are documented in EVAL-001.

The current runner releases only its own completed runtime sessions through the
native stop endpoint and waits for confirmed release before continuing. It does not
stop suspended/active sessions or delete history. This is evaluator cleanup, not a
change to the interactive application's session policy.

Additional opt-in experiments:

```sh
uv run --frozen --env-file .env python scripts/run_phase5_answer_experiment.py \
  --allow-provider-calls --output /tmp/phase5-answer-new.json
uv run --frozen --env-file .env python scripts/check_phase5_similarity.py \
  --allow-provider-calls --output /tmp/phase5-similarity-new.json
```

The first permits at most three generations and three grades; the second uses two
contextual query batches. Neither changes production data. Their failures and
negative findings must be retained rather than selecting only favorable results.

## Expanded semantic admission validation

The requester selected broader semantic validation rather than exact-query-only
reuse. Freeze [semantic-cache-v2.json](../../examples/telecom/evaluation/semantic-cache-v2.json)
before provider calls. It includes four topical groups, 48 equivalence comparisons
and 24 explicit scope-denial checks; development and held-out questions do not overlap.
Labels concern query equivalence, not independently annotated source relevance.

```sh
uv run --frozen --env-file .env python scripts/run_phase5_semantic_validation.py \
  --allow-provider-calls --output /tmp/phase5-semantic-expanded-new.json
```

This uses 12 bounded contextual embedding requests and the real cache index plus
production lookup code. Four temporary references use a random tenant and vacant
fixed slots; occupied application rows are never intentionally overwritten. Cleanup
is restricted to that random tenant, including after a failed probe. An overwritten
test slot invalidates the run. Source resolution is synthetic: this validates cache
admission and filters, not the downstream final answer or source recall.

The historical expanded screen kept 0.99 fixed; it preceded the v3 calibration. Report precision, equivalent recall, false
hits and missed equivalents by partition. Explicit scope changes are distinct from
product/firmware words inside a question; the runtime must not assume those words
change authenticated scope. Admin inspection of index readiness is separate from
the cache identity: do not broaden its role to list or administer search indexes.

## Source recall: warm cache versus fresh hybrid retrieval

Freeze [cache-source-recall-v1.json](../../examples/telecom/evaluation/cache-source-recall-v1.json)
before execution. Thirty-two synthetic procedures have explicit product/alarm
applicability labels. Twelve questions are split into development and held-out
families. The corpus exceeds the 20 candidates stored in a cache entry.

```sh
uv run --frozen --env-file .env python scripts/run_phase5_source_recall.py \
  --allow-provider-calls --output /tmp/phase5-source-recall-new.json
```

Budget: 16 document embedding calls (both required schema dimensions produced by
the provider), three query embedding calls, and at most 24 reranks. The experiment
uses the existing isolated evaluation collection and scoped cache identity; no new
indexes or roles are required. Native hybrid fusion uses exact vector search for
this baseline and retains 20 candidates. Actual production cache lookup determines
hits at the unchanged threshold. Reranking is repeated for the current question.

Record candidate recall before reranking, ranked source IDs and top-1/top-3 metrics
for fresh and warm paths. On a cache miss, the effective result is the fresh path;
do not label that a successful semantic hit. All temporary evaluation/caching rows
are removed by their random run identity. Query text does not override trusted scope.
Synthetic corpus labels are not publication approvals or final-answer correctness.

## Development-only threshold calibration

The [v2 calibration dataset](../../examples/telecom/evaluation/cache-source-calibration-v2.json)
freezes five threshold candidates and a selection rule before execution: choose the
highest threshold with at least 50% development paraphrase reuse, no candidate recall
or top-one regression, and all effective development top-one results correct. If no
candidate qualifies, do not use validation to rescue the choice.

```sh
uv run --frozen --env-file .env python scripts/run_phase5_source_recall.py \
  --allow-provider-calls --calibrate \
  --dataset examples/telecom/evaluation/cache-source-calibration-v2.json \
  --output /tmp/phase5-calibration-new.json
```

The eight held-out questions are new and disjoint from previous datasets. A selection
is saved before any held-out retrieval/reranking results are observed; query embedding
batches may be computed earlier. Selection functions refuse held-out rows. Runtime
cache threshold changes are confined to this offline evaluator process and restored
after lookup; no deployed configuration is changed. Actual MongoDB similarity scores
support counterfactual development comparisons without repeating provider calls at
every threshold. Budget: 16 document embedding calls, four query embedding calls,
and at most 32 reranks. Actual cache hits use the selected threshold during validation.

Synthetic same-author questions and reused source templates limit generalization.
A successful experiment alone does not claim production quality or acceptance of
an unrelated model, corpus, or equipment scope.

## Calibration v3: coverage across wording groups

The v2 held-out observations are explicitly promoted to development in
[calibration v3](../../examples/telecom/evaluation/cache-source-calibration-v3.json).
They are no longer independent validation. The 40-source corpus adds unrelated
billing/Wi-Fi procedures to expose candidate recall loss on inappropriate reuse.
Each development anchor group must independently reach the minimum paraphrase hit
rate. The highest qualifying threshold is frozen before two new held-out groups.

```sh
uv run --frozen --env-file .env python scripts/run_phase5_source_recall.py \
  --allow-provider-calls --calibrate \
  --dataset examples/telecom/evaluation/cache-source-calibration-v3.json \
  --output /tmp/phase5-calibration-v3-new.json
```

Budget: 20 document embedding calls, at most nine query embedding calls and 68
reranks. Shared negative queries are embedded once. The new held-out questions
must not tune the selection; each validation anchor group must also meet the
minimum before bounded acceptance. No new indexes, credentials or services are
created. Existing random-run cleanup and phase boundaries still apply.

Current runtime: workflow 8, deployed build `bld_01M691YPABN60FEKHW6E1KZGB5`,
deployment `deploy-af009ed4`; source hashes and health evidence are linked from
EVAL-001. The calibrated threshold is 0.91. Earlier evidence retains its original
0.99/0.98 values and does not describe the current runtime.

To repeat the bounded cache validity proof, use a fresh output path:

```sh
uv run --frozen --env-file .env python scripts/check_phase5_cache.py \
  --output /tmp/phase5-cache-validity-new.json
```

This proof refuses to replace an existing application entry for its fixed query.
Run it in an idle demo or choose a separate reviewed synthetic probe; do not delete
an interactive user's entry to force the check to pass.
