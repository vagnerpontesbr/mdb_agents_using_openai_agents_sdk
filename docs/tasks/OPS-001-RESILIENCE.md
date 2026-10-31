# OPS-001: Scalability and resilience

- Status: Complete for the requester-approved demo scope; manual publication pending
- Owner: Telecom demo maintainer
- Dependencies: RUN-001, EVAL-001, RAG-001, MEM-001
- Plan: [Scalability and stress tests](../SCALABILITY_AND_STRESS_TESTS.md)
- Runbook: [Phase 8](../runbooks/PHASE_8.md)

## Accepted decisions — 2026-10-31

The requester initially authorized USD 10, then raised the total Phase 8 provider
budget to **USD 30**. The requester confirmed Agent Engine preview is uncharged
and selected retaining the current provider path: OpenAI model calls remain direct;
Voyage knowledge calls use the configured MongoDB AI Gateway. Include both billable
paths in the total. No provider migration, cluster tier increase, shared policy
change or new infrastructure subscription is implied. Prior phase consumption is
historical; new Phase 8 provider work must be recorded separately.

The current OpenAI Standard rates were read from the
[official pricing page](https://developers.openai.com/api/docs/pricing): gpt-5.6-luna
short-context input USD 0.20/M, output USD 1.20/M, cached input USD 0.02/M, and cache
writes USD 0.25/M (30 minutes) or USD 0.50/M (12 hours). These prices alone do not
establish gateway/memory charges or the billed total. Do not report missing cost as
zero. Engine limits constrain calls/duration; they are not a USD billing ledger.

## Acceptance criteria

- Reproducible isolated manifests, runners, results and readable reports.
- Separate local doubles, real Atlas resources and real Engine/provider results.
- Verify session/tenant boundaries, native duplicate admission, overload recovery,
  worker lease recovery and governed source/cache correctness under concurrency.
- Measure ingestion contention independently of interactive capacity.
- Define workload-specific SLO/resource/cost limits before acceptance runs; label
  short baseline work as characterization, not production capacity.
- Exercise planned soak/arrival-rate/scale-out profiles within resource budgets;
  keep partial/failed runs and stop on invariant violations.

## Local HTTP baseline

The [versioned workload](../../examples/telecom/load/http-mock-v1.json) drives the
real FastAPI application over loopback HTTP with 1/2/4 Uvicorn worker processes.
Identity and Engine transport are explicit test doubles. Temporary SQLite stores
only the Engine double's shared synthetic state; it is not a new application
memory/approval owner or an Atlas substitute in acceptance claims. Child processes
receive no inherited provider credentials and do not load dotenv files.

[Measured JSON](../../compatibility/phase8-http-characterization.json) and the
[HTML report](../../compatibility/phase8-http-characterization.html) record all 15
combinations of concurrency 1/5/10/25/50 and 1/2/4 workers. The short closed-loop run
completed in 4.662 seconds: 546 chat requests offered, 207 completed, 339 rejected
by the existing eight-active-requests-per-process boundary. Every completed result
was exact, recovered, and denied to the other synthetic user. There were 107
cross-process recoveries against the shared Engine double. Injected dependency
failure produced an SSE error, never a success, and post-load health checks passed.

The [initial stopped run](../../compatibility/phase8-http-initial-stopped.json)
incorrectly treated expected admission 503s as invariant failures and stopped after
two stages. The corrected runner counts only the exact admission response as
rejection, verifies completed work after the load settles, and does not retry chat.
This correction changes the harness, not application admission limits.

These samples do not establish peak/stable capacity, Atlas performance, native
Engine scale-out, authentication hashing cost, ingestion isolation, voice latency,
resource saturation, or a soak SLO. The HTML table is a local measured dashboard,
not a monitoring deployment. Source/profile/lock hashes identify the local code;
the Git head records the published Phase 7 base, not publication of these changes.

## Final requester decision and completion

After the bounded profiles passed, the requester explicitly stated that proof of
production capacity and prices is not required, and requested committing the work.
This supersedes the earlier billing-reconciliation gate. Phase 8 is complete for
the approved demo scope; no additional capacity or pricing investigation is needed
for acceptance. The nine planned phases (0–8) are complete for that scope.

Historical accounting evidence remains unchanged: unavailable prices are still
unknown, not zero or verified. The existing USD 30 authorization is not increased
by this scope decision. No further paid experiment is scheduled. Proposed broader
production/capacity experiments are optional extensions, not pending demo gates.
Measured limitations remain documented and are not production guarantees.

Publication remains manual. Phase 8 source/evidence is local and ready for commit;
no Phase 8 commit, push, remote CI result or hosted redeployment is claimed.

## Bounded real Engine checkpoint

[Native concurrency evidence](../../compatibility/phase8-engine-concurrency.json)
records six invoke attempts: five completed and one native same-session conflict.
Baseline, two distinct sessions, same-session contention and the post-concurrency
control passed. Every completed execution returned the exact synthetic invoice,
denied the other user and remained recoverable after its runtime was released.
The first launcher attempt failed on a local module import before any provider
call; the import was corrected before the recorded run. No uncertain call was retried.

[Native trace metrics](../../compatibility/phase8-engine-trace-metrics.json) record
five session-scoped observations, 15 model calls, 13,009 observed tokens and five
expected invoice tool selections. These token counts exclude unobserved managed
memory/provider work; the total billed USD amount remains unavailable. There is
no claim of zero provider cost or full budget reconciliation.

## Approved provisioning and historical failures

The requester explicitly approved the exact resource proposal with digest
`08d5205f05d39fc2b5604e4bc500b91456488f070ef508c03d039dd7adcb91cd`.
The [first apply attempt](../../compatibility/phase8-provisioning-attempt.json)
stopped at expired Atlas authentication before mutations. After login renewal,
the same plan was applied. This prerequisite is resolved, not an outstanding
request for authorization. Constructor controls follow
[ADR-0029](../adr/0029-isolated-load-environment.md).

## Applied resources and isolated domain acceptance

After the requester completed Atlas CLI login, the approved plan was applied with
its unchanged digest. [Provisioning evidence](../../compatibility/phase8-resource-evidence.json)
records eight new collections, seven ordinary indexes and three search/vector
indexes. Four scoped users were created. The previously recorded login prerequisite
is resolved; no new approval was requested for the same plan.

[Role evidence](../../compatibility/phase8-role-evidence.json) passed **208**
permission controls, including denial of demo identities against load namespaces.
All strict validator definitions matched the plan. All three search/vector indexes
were READY/queryable. The first role probe stopped with OperationFailure before
recording a check; its [failed evidence](../../compatibility/phase8-role-initial-stopped.json)
is preserved. The error code was not captured, so no specific cause is asserted.
The subsequent complete role probe passed; authorization is not inferred from that
initial failure or from a missing positive control.

[Ingestion evidence](../../compatibility/phase8-ingestion-evidence.json) passed
concurrent submission deduplication, the four-job admission ceiling, other-tenant
claim denial, actual child-process termination after a durable claim, stale-worker
fencing, duplicate completion rejection and exact quota release after exhausted
attempts. Lease expiry uses an injected domain clock, not a six-minute real-time
outage. No OCR or provider call occurs in this fault profile. The stopped child is
owned by the probe; no deployed API, Engine or other worker was stopped.

[Cache concurrency evidence](../../compatibility/phase8-cache-concurrency.json)
passed a positive native vector-cache lookup, tenant/ACL denial and four in-flight
response denials when the source was revoked at a controlled reranking barrier.
The final backend source check blocked release even though the cache had matched.
Vectors and reranking are synthetic and the approval receipt is a seeded fixture;
this proves the exercised database/governance interleaving, not RAG quality or a
new native-review integration. No paid provider calls occurred in these probes.

MongoKnowledgeAuthority now has the same strictly boolean, keyword-only load
selection as the other three adapters. The default remains demo-only and HTTP
requests cannot select namespaces. Synthetic failed jobs and revoked knowledge
fixtures remain only in load databases; no demo records were modified.

The subsequent sustained, telemetry and voice profiles are recorded below. Full
provider billing remains unreconciled. Results are bounded demo measurements,
not production capacity acceptance.

Follow-up validation passed: 137 backend tests, Ruff, mypy and repository checks.
The [clean-child-environment rerun](../../compatibility/phase8-ingestion-clean-env-evidence.json)
repeated the ingestion controls with only PATH inherited by the child; all seven
controls passed. Configured load credential values were absent from changed
versionable text files. Credentials remain in ignored `.env.phase8`.

## Test environment and tier history

The requester clarified that Phase 8 uses M20 and previous phases used M10.
[Read-only control-plane evidence](../../compatibility/phase8-environment-evidence.json)
confirms **OpenAI-SDK M20** on AWS `US_EAST_1`, MongoDB 9.0.4, at the observation
time. The separate Engine-memory cluster **ClusterDemoTelco is M30_GEN_2** in
the same region/version. The user statement describes the application test tier;
it does not overwrite the independent memory-cluster observation or establish its
historical tier. Preserve earlier evidence and do not compare M10/M20 performance
without a controlled experiment. Local HTTP/Docling results are local-machine
measurements and do not measure M20 throughput.

## Real voice during offline ingestion

[Voice evidence](../../compatibility/phase8-voice-contention.json) passed three
real provider attempts without retries: baseline TTS, then concurrent TTS/STT
while one CPU Docling process converted the existing synthetic scanned PDF.
Baseline TTS took 4.422 seconds; concurrent TTS took 3.013 seconds and STT took
1.576 seconds. Both calls finished while Docling was alive. Docling extracted two
pages in 6.894 seconds. WAV format, audible PCM, transcript invoice/amount and
45-second speech deadlines passed. Audio remained transient; none was committed.

These are isolated provider-stage timings, not statistically meaningful latency
percentiles or a new human listening/noisy-environment acceptance. One CPU job does
not establish ingestion saturation. Provider models and routing are unchanged.

## Cost accounting limitation

[Accounting evidence](../../compatibility/phase8-cost-evidence.json) records a
successful workspace-scoped seven-day Engine cost-dashboard read. All 211 calls
were `unpriced_llm_calls`; its numeric zero cannot be treated as a zero invoice.
The window includes previous phases and cannot attribute all its tokens to Phase 8.
The first read returned HTTP 401; renewing the private CLI token resolved it.

The 15 Phase 8 observed model calls contain 11,898 input and 1,111 output tokens.
At the recorded uncached Standard rates, their narrow estimate is USD 0.0037128.
This excludes voice, managed memory and any unobserved gateway work, and is not a
bound on total billing. The three voice calls produced 15.35 seconds of TTS audio
and transcribed 7.9 seconds; the SDK evidence does not expose a complete bill.

The official OpenAI organization Usage/Costs example requires an Admin Key;
neither supported admin-key environment variable is configured. No credentials
were printed or manufactured. Total billed cost remains **null**, the USD 30
ceiling remains unchanged. No further paid load is scheduled. This historical
accounting gap is not an acceptance blocker following the final requester decision.

## Sustained read-only Atlas checkpoint

[Atlas evidence](../../compatibility/phase8-atlas-read-evidence.json) passed 300
open-loop native hybrid/governance operations over five minutes at one operation
per second, with zero errors and p95 2,092.594 ms below the predeclared 5,000 ms
limit. The test used one reused scoped reader client, at most four concurrent
operations, synthetic vectors and the existing isolated revoked-source fixture.

One hundred requests each tested authoritative revocation, other-tenant denial
and other-ACL denial. Initial/final positive controls confirmed the stale chunk
remained searchable while the source remained revoked. No request reached the
reranker or released the procedure. No document was modified. These measurements
cover one source and cannot establish M20 peak throughput, search saturation,
representative RAG quality or production capacity.

## Completed sustained local profile

[Measured JSON](../../compatibility/phase8-sustained-evidence.json) and
[HTML report](../../compatibility/phase8-sustained-evidence.html) passed all seven
windows in **2,147.333 seconds**. The full profile offered **13,650** journeys,
completed **12,812**, and rejected **838** through the expected admission control
in the spike. There were zero unexpected errors or generator drops. All normal
windows had zero rejections. The 30-minute soak completed all **9,000** journeys
at **5 offered journeys/second**, including the 20% synthetic voice mix.

| Window | Offered | Completed | Rejected | Chat p95 ms | Synthetic voice p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| warmup | 600 | 600 | 0 | 72.945 | 190.753 |
| chat_baseline | 150 | 150 | 0 | 74.875 | — |
| voice_baseline | 150 | 150 | 0 | — | 192.503 |
| ingestion_contention | 600 | 600 | 0 | 63.859 | 171.889 |
| spike | 3000 | 2162 | 838 | 62.624 | — |
| recovery | 150 | 150 | 0 | 75.167 | 198.133 |
| soak | 9000 | 9000 | 0 | 73.994 | 192.05 |

The soak's first-event p95 was 8.773 ms; sampled loop-lag p95 was 2.083 ms.
Peak RSS was 238.359 MiB for the API process tree, 49.5 MiB for the generator and
1,635.141 MiB for offline Docling. Maximum API RSS above the post-warmup sample
was 9 MiB, below the 128 MiB ceiling. Sampling cannot rule out shorter peaks or
all memory leaks. Twenty real text/scanned PDF jobs completed outside the API.
The local profile performed 1,279 sampled recovery/access checks, including 126
recoveries served by a different process during the spike.

The 5-RPS result is a tested offered rate for this configuration, not a measured
maximum. Replica IDs appeared across the run, but keepalive distribution was not
balanced; no scale-efficiency claim follows. Identity/Engine/voice remain doubles;
real native Engine, Atlas and speech evidence are the separate profiles above.
Docling contention is real but does not cover queue-to-embedding throughput or
CPU saturation. All owned load processes were stopped by the runner.

Final local verification: **138 backend tests** and **86 hosted contract tests**
passed; Ruff, mypy, script F/I checks, repository links/ADR checks and diff whitespace
checks passed. The configured private credentials, including all four load-user
passwords, were absent from changed versionable text files. `.env` and `.env.phase8`
are ignored. Application/SDK locks and the hosted deployment were not changed.
