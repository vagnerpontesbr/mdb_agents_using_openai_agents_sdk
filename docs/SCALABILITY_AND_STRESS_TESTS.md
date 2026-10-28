# Service boundaries and stress-test plan

Status: design only; no benchmark has been run and no capacity is claimed.

## Deployable boundaries

| Process/service | Responsibility | Scale and ownership |
|---|---|---|
| API/BFF and voice transport | Authentication, quotas, client contracts, SSE/audio connections | Scale by active connections and ingress CPU; no OCR or business state in process memory |
| Agent runtime | Supervisor/specialists, tool execution, approvals, channel-independent workflow | Scale by in-flight runs/provider quotas; owns run state and application session coordination |
| Knowledge service | Governance, retrieval/reranking, publication, retrieval cache | Scale by QPS and search latency; owns document/chunk/governance/cache writes |
| Ingestion workers | PDF extraction/OCR, contextual chunking, embedding | Scale by bounded queue age and CPU/RAM; submit staged artifacts through knowledge contracts |
| Engine memory | Official short/long-term memory service | Respect provider ownership, limits, and documented integration contract |
| Business connectors | Simulated CRM/BSS/OSS initially, later real adapters | Initially modules in runtime; separate services only for demonstrated ownership/isolation/scaling needs |

Use a monorepo with shared typed contracts, independent process entrypoints and health/readiness checks. Local orchestration can start all processes together. Load-profile orchestration gives each replicas/resource limits independently. A shared cluster remains a shared bottleneck; measure index contention and total connection pools. Avoid cross-service collection writes and distributed transactions spanning providers.

Internal calls propagate authenticated service identity, tenant context, request ID, deadline, and idempotency key. APIs/events are versioned. Document a single retry owner per operation, bounded queues, cancellation propagation, shutdown draining, and admission control. Separate interactive and ingestion concurrency budgets. A durable outbox/worker lease design is required before scaling consumers; queues use at-least-once semantics.

## Experiment profiles

Use a Python load generator such as Locust for HTTP and appropriate streaming clients for SSE/audio; validate protocol support before selecting plugins. Ordinary HTTP response time is insufficient for streaming. Record the load generator's own resource saturation.

1. **Infrastructure profile:** deterministic LLM/embedding/business doubles with configurable latency/errors, real service processes, and a declared database/search configuration. Synthetic vectors cannot establish retrieval quality. This profile isolates application capacity.
2. **Provider integration profile:** bounded real OpenAI/Voyage/MongoDB/Engine calls with known quotas and a declared total spend cap. Keep results separate; a provider 429 is not proof of application CPU saturation.
3. **Resilience profile:** injected provider delays/429/5xx, worker termination, lease expiry, disconnects, and failed publication against isolated test resources.

Each run manifest records commit, locks, models, index configuration, corpus size, chunk distribution, tenant count, hardware/replicas, Atlas tier/region, quotas, workload mix, cache state, random seed, clock, and policy version.

## Initial workload ladder

Proposed configurable experiment, not a promised capacity: 1 → 5 → 10 → 25 → 50 concurrent interactive sessions. Warm up for 2 minutes and hold each step for 5 minutes; observe recovery between profiles. Use a 30-minute soak at the last stable level, a bounded spike, and scale-out comparison with 1/2/4 replicas where resources permit. Start real-provider runs at the lowest level; advance only within spend/quota limits.

Exercise chat and voice separately before a combined mix (initial hypothesis: 60% technical chat, 20% financial/sales chat, 20% voice). Repeat with warm cache, cold cache, long histories, skewed hot tenants, and small/large text/scanned PDF ingestion running concurrently. Define audio duration, arrival rate, think time, token sizes, and job submission rates in the manifest rather than reporting concurrency alone. Include open-loop arrival-rate runs to reveal queue buildup; record offered, accepted, and completed load.

## Measurements and pass/fail

- Throughput: completed successful conversations and jobs per unit time, plus offered/accepted requests and rejected load.
- Latency: p50/p95/p99 for admission, first safe event, complete answer, first useful audio, tools, retrieval, and ingestion queue wait; report sample counts and errors alongside percentiles.
- Resources: CPU/RAM, event-loop lag, active streams/runs, queue age/depth, database/search latency, connection pools, index lag, provider quotas, and tokens/cost per successful task.
- Correctness: no cross-tenant access, duplicate business effects, unauthorized actions, or expired/superseded-source use in the test cases; measure quality under load against the unloaded baseline.
- Recovery: bounded backlog drain, reclaimed jobs without duplicate publication, reconnect/resume correctness, and no monotonic memory growth during soak.

Before an acceptance run, write workload-specific latency/error/recovery/cost thresholds from baseline and business objectives. A run without these is characterization, not a passed SLO test. Stop immediately on invariant violation; also stop at budget exhaustion or declared resource/queue ceilings. Persist the reason and partial results. Report the highest stable offered load for the tested configuration, bottleneck, scale efficiency, cost, and limitations. No production capacity extrapolation from mock-provider throughput.

## Deliverables and acceptance

Implementation adds versioned workload manifests, a repeatable runner, dashboards, result artifacts, and a runbook. Demonstrate that ingestion saturation does not exhaust interactive worker resources, scale-out preserves session correctness, and governance still blocks the stale-document fixture during cache hits and concurrent updates. Production readiness remains outside this non-production asset's claim.

## Single-cluster constraint

All Atlas-backed demo, evaluation, and load namespaces use exactly one cluster, with separate identities and service/domain databases. An isolated load environment means processes, credentials, and logical data isolation, not a second Atlas cluster. Schedule disruptive tests, enforce budgets, and measure shared-resource contention. The negative-control database must be inaccessible to demo roles. See [data architecture](DATA_ARCHITECTURE.md).
