# Phase 4: Governed PDF knowledge

Historical phase-specific evidence and versions follow. Use [Phase 7](PHASE_7.md)
for the active runtime and [publication status](REPOSITORY_SETUP.md) for current Git/CI.

The authoritative acceptance status and portable evidence are in
[RAG-001](../tasks/RAG-001-KNOWLEDGE.md). The approved ownership and native
publication boundary is [ADR-0026](../adr/0026-governed-knowledge-publication.md).

## Run the demo

The ignored private environment supplies application identity, separate knowledge
reader/publisher and ingestion URIs, and Voyage key/base. Never print these values.
The private authenticated Engine CLI session is permitted only in the loopback
backend. Build the UI, then start with both feature flags:

```sh
npm --prefix apps/web run build
APP_KNOWLEDGE_ENABLED=true APP_JOURNEY_ENABLED=true \
APP_ORIGIN=http://127.0.0.1:53185 APP_WEB_DIST=apps/web/dist \
uv run --frozen --env-file .env uvicorn telecom_app.api:application \
  --factory --host 127.0.0.1 --port 53185
```

1. Sign in. Users can search eligible knowledge and download its original PDF.
2. Administrators upload a PDF with source dates and version metadata. For a
   replacement, supply the exact current version key in `supersedes`.
3. Run the separate worker and inspect the staged job. It does not publish content.
4. The registered information owner requests native publication review, inspects
   the exact request and approves or rejects their own request.
5. After approval, publish. The backend verifies the completed Engine outcome and
   exact source before the domain transaction. Refresh sources and search.
6. In chat, ask for the approved optical procedure. The technical specialist returns
   exact excerpts and document/version/page citations. The agent ingestion tool
   accepts an uploaded job ID and requires owner entitlement; it does not run OCR.

Initial owner registration uses the existing initial administrator's internal ID.
Another admin can prepare documents but cannot grant ownership or approve on the
owner's behalf. Native reviews expire after five minutes; obtain a new review when
expired. Jobs remain `staged` after publication because publication does not write
another service's ingestion state; use the published source list for active versions.

## Limits and lifecycle

The demo fixes tenant `synthetic-telecom`, ACL `synthetic-support`, product FiberBox,
region demo, firmware 2.x and English. PDF input is at most 5 MB and ten pages;
tables are rejected. Docling runs in the separately locked CPU Python 3.14.6
environment; the application remains Python 3.15.2. The outer extraction deadline
is 270 seconds. Voyage context-4 uses 1,024 dimensions and native contextual
chunking; queries use native MongoDB hybrid fusion and rerank-3.

Four active jobs per tenant, a six-minute fenced lease and two attempts bound
admission and crash recovery. Explicit processing failures are terminal. A crash
can repeat a paid provider call. There is no automatic requeue endpoint, corpus
quality guarantee or production capacity claim. Candidate count is bounded to 20.
Exact excerpts above the response budget cause abstention (7,500 characters locally,
1,800 inside the hosted business-result boundary).

Originals, staged artifacts and superseded source history remain stored. Physical
cleanup requires a separate document lifecycle implementation; these are application
records, not Engine-managed memory. The user's accepted native thirty-day memory
retention remains unchanged. Request-time authoritative checks exclude revoked,
expired, overdue or superseded knowledge even while search indexes lag. No answer
cache is implemented.

## Resources and reproduction

The approved [Atlas proposal](../../compatibility/phase4-resource-plan.json)
contains seven collections, five classic indexes, two search indexes and three
scoped roles/users on OpenAI-SDK. All seven validators are strict/error. The
[shared Engine proposal](../../compatibility/phase4-engine-policy-proposal.json)
adds exactly three tool names; its separate user approval has been applied.
ClusterDemoTelco and unrelated policies are unchanged.

Bounded deterministic checks:

```sh
uv run --frozen pytest -q
uv run --frozen ruff check src/telecom_app tests/foundation
uv run --frozen mypy
uv run --project compatibility/hosted-runtime --frozen --no-sync \
  python -m unittest discover -s tests/hosted_contract -q
npm --prefix apps/web run lint
npm --prefix apps/web run build
npm --prefix apps/web test
npm --prefix apps/web run test:e2e
python3 scripts/check_repository.py
git diff --check
```

Live probe scripts require injected credentials and incur documented provider calls:
`check_knowledge_provider.py`, `check_ingestion.py`, `check_knowledge_storage.py`,
`check_knowledge_resources.py` and `check_knowledge_invalidation.py`.
Read each script's scope before execution. Invalidation temporarily changes and
restores the synthetic source to exercise stale-index exclusion. Publication probe
`check_publication.py` creates an initial source; do not rerun it for an existing
document without binding its current version as an explicit replacement. These
operator probes are separate from browser authentication acceptance.
