# Phase 8: Scalability and resilience

[OPS-001](../tasks/OPS-001-RESILIENCE.md) owns scope, decisions and acceptance.
Phase 8 is complete for the approved demo scope; manual publication is pending. Phase 7 commit `610ca8b` passed CI run `41207595549`.

## Local HTTP characterization — no providers

From the repository root, choose a new output path:

```sh
uv run --frozen python scripts/run_phase8_http.py --output /tmp/telecom-http-load.json
```

The runner creates isolated temporary state, starts 1/2/4 API worker processes on
loopback, runs the fixed bounded manifest, and shuts down only its own processes.
No Atlas, Engine, model, embedding or voice provider is called. JSON and adjacent
HTML are produced; an existing JSON output is rejected. No local credentials are
passed into worker processes. All state is synthetic and removed with the temporary
directory. SQLite belongs only to the Engine transport double.

There are at most 546 chat requests plus one injected failure per stage, with
additional post-load scope/recovery and health checks. Each request has a ten-second
timeout and the experiment has a 180-second wall budget. Rejections are not retried.
The first SSE progress event and final response have separate latency metrics.
HTTP 200 alone is not success: the final event and exact result must match.
Expected admission 503s are counted separately from uncertain execution failures.

Do not extrapolate these short samples to production capacity. Real authentication,
Atlas/search, model latency, voice and OCR are excluded. The profile is
characterization, not the proposed sustained/soak acceptance workload.

## Bounded native Engine profile

First inspect the zero-call plan:

```sh
uv run --frozen python scripts/run_phase8_engine.py --output /tmp/telecom-engine-load.json
```

The live variant requires the existing private CLI login, private application
configuration and two existing synthetic accounts. The private account JSON is an
array containing email, password and expected user_id; never commit it or tokens.
Use a new evidence destination:

```sh
uv run --frozen --env-file .env python scripts/run_phase8_engine.py \
  --allow-live --accounts-file /private/path/synthetic-accounts.json \
  --output /tmp/telecom-engine-load.json
```

At most six invoke attempts, concurrency two: single baseline, distinct sessions,
same-session contention and a post-concurrency control. Exact synthetic invoice
text, other-user denial and completed-state recovery after native runtime release
are required. There is no automatic invoke retry, business mutation, shared policy
edit or workspace-wide runtime stop. On uncertainty, inspect the exact recorded
session before further calls; preserve failed evidence.

The USD 30 authorization includes both current direct OpenAI and gateway paths.
Engine preview is uncharged per requester. A six-attempt bound is not a verified
billing amount; inspect native usage and provider accounting before increasing the
profile. Managed-memory/provider overhead must not be silently excluded from totals.

## Deterministic verification

```sh
uv run --frozen pytest -q tests/foundation/test_load_harness.py
python3 scripts/check_repository.py
```

The isolated Atlas resources and bounded worker/governance controls below passed.
Use OPS-001 for measured results and the final requester decision. Do not mark the phase
complete from initial characterization alone.

## Review and apply the isolated Atlas proposal

Inspect [the exact plan](../../compatibility/phase8-resource-plan.json) and
[ADR-0029](../adr/0029-isolated-load-environment.md). The command below is a
zero-call dry run that prints the exact plan digest:

```sh
uv run --frozen python scripts/apply_phase8_resources.py
```

Only after approval of this exact plan:

```sh
uv run --frozen --env-file .env python scripts/apply_phase8_resources.py \
  --approved-sha256 08d5205f05d39fc2b5604e4bc500b91456488f070ef508c03d039dd7adcb91cd
```

Provisioning uses one reused administrative client and a 15-second operation
budget; it preserves default pool settings. New runtime users receive only the
collection privileges in the plan. Check role denials, index readiness, operation
latency and connection usage before increasing load; monitor the shared cluster
because namespace separation does not reserve CPU, connections or search capacity.
Source/plan drift, existing resource drift and missing private credentials fail
closed. No existing validator, role or document is overwritten.

## Isolated Atlas checks after provisioning

The approved plan has been applied. Use fresh output paths to preserve earlier
reports. These commands write synthetic fixtures only to the approved load
namespaces and make no model/embedding provider calls:

```sh
uv run --frozen --env-file .env python scripts/check_phase8_resources.py --output /tmp/phase8-roles.json
uv run --frozen python scripts/check_phase8_ingestion.py --output /tmp/phase8-ingestion.json
uv run --frozen --env-file .env python scripts/check_phase8_cache.py --output /tmp/phase8-cache.json
```

Role probes use aborted transactions. Ingestion uses four concurrent submitting
threads and a real child worker terminated after its durable claim. The subsequent
lease expiry is controlled by the injected domain clock. The cache probe seeds one
synthetic document and receipt, pauses four reads during reranking, then revokes
the source and verifies all four final releases are denied. Source text/vectors
and the reranker are fixtures; this is not fresh provider quality evidence.

A shared client per runtime identity allows at most five pooled operation
connections for four probe threads. Probes use the existing 15-second operation
budget and no prewarmed pool. The worker child receives no inherited provider/admin
configuration and reads only its restricted load credential. The operator identity
is used only for the one isolated owner fixture, not for normal query/worker work.

No deployed worker, Engine runtime or demo document is stopped or modified by
these probes. Isolated fixtures are retained for inspection; record their generated
tenant IDs before any future cleanup, which must never target an unscoped database.

## Sustained local transport and offline Docling

```sh
uv run --frozen python scripts/run_phase8_sustained.py --output /tmp/phase8-sustained.json
```

The fixed [manifest](../../examples/telecom/load/sustained-v1.json) starts two API
workers, warms up for two minutes, separates chat/voice baselines, overlaps mixed
traffic with up to 20 offline text/scanned Docling jobs, injects a ten-second
300-RPS spike, verifies recovery, and holds mixed traffic at 5 RPS for 30 minutes.
The full run offers 13,650 journeys and has a 2,400-second wall ceiling. Normal
windows require zero errors, rejections and generator drops. The spike permits
explicit admission rejection but never incorrect successful responses.

Predeclared normal p95 ceilings are 500 ms for chat, 1,500 ms for synthetic voice
transport and 200 ms for first SSE event. Sampled loop-lag p95 must stay below
100 ms. Process-tree RSS is capped at 1 GiB for API, 512 MiB for generator and
3 GiB for ingestion, with at most 128 MiB API growth after warmup. Samples are
five seconds apart; short resource peaks may be missed. `ps` CPU is an indicator,
not a calibrated utilization measurement. The adjacent HTML reports memory and
per-window results. `--smoke` shortens the profile for harness verification and
does not establish soak acceptance.

API identity, Engine and speech are doubles. The PCM is a tone. CPU Docling is
real, runs outside the API using the isolated ingestion interpreter, and receives
offline model flags and no provider credentials. Existing cached model weights
and the synthetic PDFs under `artifacts/compatibility/pdf` are prerequisites.
No audio or extracted document output is retained by the runner. Source and lock
hashes are included. This measures local transport/CPU behavior, not Atlas or
real-model throughput, nor an end-to-end ingestion/embedding queue under load.

## Read-only Atlas hybrid profile

```sh
uv run --frozen python scripts/run_phase8_atlas_reads.py --output /tmp/phase8-atlas-reads.json
```

This reuses the tenant in the successful cache-revocation evidence, preserves its
revoked status, and reads through only the scoped knowledge-reader identity.
A positive control confirms the deliberately stale chunk remains searchable while
the authoritative version is revoked. Three hundred open-loop operations over
five minutes alternate source revocation, other-tenant and other-ACL refusals.
Each must return the exact safe response without reaching the reranker. Native
hybrid fusion is real; the vector is synthetic. The profile uses at most four
pooled operations and a 15-second operation timeout, with a predeclared 5-second
p95 ceiling and zero allowed errors. One source cannot establish corpus capacity.

## Real speech contention and accounting

The completed bounded speech evidence is in OPS-001. The runner defaults to a
zero-call plan. Reproduction is optional; no additional paid calls are needed for acceptance:

```sh
uv run --frozen python scripts/check_phase8_voice.py --output /tmp/phase8-voice.json
uv run --frozen --env-file .env python scripts/check_phase8_cost.py --output /tmp/phase8-cost.json
```

The voice runner's `--allow-live` path makes at most three attempts, without retries,
using the existing speech service. It holds synthetic audio only in memory and
overlaps TTS/STT with one offline scanned-PDF conversion. The cost script makes a
read-only workspace dashboard request. Its seven-day aggregate includes previous
phases and may have unpriced calls; `billing_unreconciled` is not a passed budget
measurement. The requester excluded pricing proof from acceptance; no Admin Key is required to close the demo phase.

Cluster-tier context is in [environment evidence](../../compatibility/phase8-environment-evidence.json)
and OPS-001: current application M20, earlier application tests M10 per requester,
and current separate Engine-memory cluster M30_GEN_2. Do not edit historical
results or extrapolate local HTTP measurements to these Atlas tiers.

The recorded full sustained profile passed all seven windows, including the complete 30-minute soak. The recorded Atlas and real-voice profiles also passed. Reproduction commands above are optional and do not imply further paid work. Production-capacity and pricing proof are not demo completion gates. See OPS-001 for exact metrics and unvalidated extensions.
