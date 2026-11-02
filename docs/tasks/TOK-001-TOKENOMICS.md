# TOK-001: Control Plane Tokenomics dashboards

- Status: TOK-0 merged in PR #16 (`3fc274c`), local/remote CI passed; TOK-1 merged in PR #17 (`cd34218`); TOK-2 merged in PR #18 (`44e69a4`); TOK-3 merged in PR #19 (`4b21bd6`), local/remote CI passed; 7/30/90-day demo scope explicitly accepted
- Requested: 2026-11-01
- Owner: Telecom demo maintainer
- Dependencies: UI-001 shell/admin boundaries; native Engine usage metadata
- Related migration: [MEM-002](MEM-002-MYMEMORY-MIGRATION.md)

## Outcome and reference

Add an admin-only `Tokenomics` item inside Control Plane at
`#/control-plane/tokenomics`. Reproduce the useful dashboard structure and visual
elements inspected in the Fiserv reference, adapted to this demo's actual data and
pt-BR/en-US/es-ES UI. This is a requested addition to [UI-001](UI-001-PROFILES-CONTROL-PLANE.md),
not a new primary tracing system or a pricing-reconciliation requirement.

Reference inspected read-only under `clientes/fiserv/gensdd-main`:
`frontend/src/components/TokenomicsPanel.tsx`, the Tokenomics/Focus interfaces in
`frontend/src/types.ts`, API methods, and `backend/app/routers/tokenomics.py` plus
`backend/app/tokenomics_service.py`. Its organizational roles, storage, locale and
FOCUS-like mappings must not be copied as Telecom authorization or billing truth.

## Dashboard inventory and adaptation

| Reference visual | Planned Telecom behavior | Data/acceptance condition |
| --- | --- | --- |
| Six KPI cards | Total cost, observed tokens, average cost per execution, cache hit ratio, token goodput, execution count | Each has units, period, coverage/source and availability state; unavailable is not zero |
| Overview: application bars and table | Current application/workspace totals, count, tokens, cost and average | This demo may have only one application; never invent other applications or query unrelated workspaces |
| Overview: daily columns | Tokens/cost over time with accessible table alternative | Gaps differ from zero; consistent UTC aggregation with explicit display timezone |
| Overview: anomaly cards | Observed metric, baseline, deviation, date and explanation | Deterministic versioned rule and adequate comparable baseline; otherwise show insufficient data |
| Breakdown: context bars | Instructions, history, semantic memory, RAG chunks, tool results, user input, reasoning-token count, final answer | Use only supported measured attribution; unmeasured components appear unavailable/unattributed; no raw prompts or hidden reasoning |
| Breakdown: token-category bars | Input/output/cached-input or other provider-reported categories | Define overlapping versus disjoint categories to prevent double counting |
| Breakdown: model bars | Models with language/embedding type and observed usage | Unknown type/usage remains unknown; preserve reported model identity |
| Breakdown: agent bars | Supervisor and specialists where native attribution is available | Do not infer distribution from total session tokens |
| Breakdown: intent table | Existing typed journey/business category where observed | No new ontology or intent classifier; unavailable category is explicit |
| FOCUS tab | Paginated period/SKU/provider/consumed-quantity/unit/billed-cost table | FOCUS-like presentation only unless standard conformance is separately validated; estimates must never populate BilledCost |

All three tabs (`Overview`, `Breakdown`, `FOCUS`) and all listed sections are in
scope, including meaningful empty/unavailable states. Visual parity does not require
fabricated telemetry. The requester explicitly accepted 7/30/90 trailing-day presets for the demo
with "sim aceito" on 2026-11-01 (local time). This supersedes the earlier custom
historical-range requirement; apply the supported filters server-side. Prefer token bars when monetary values
are unavailable, and label the selected metric. Actual zero produces a zero-length
bar, not the reference's minimum nonzero bar. Tooltips must work by keyboard too.

## Data ownership, semantics and contracts

Engine remains the primary owner of traces and execution state. FastAPI exposes
sanitized, admin-authorized derived views over supported native usage/cost APIs.
Do not create a second SDK trace owner or browser-direct Engine connection.
Any future persisted aggregate is rebuildable, scoped application-owned metadata,
not a memory copy; introduce storage/retention only after a concrete need and design.

Implemented TOK-1 read-only endpoints:

- `GET /api/admin/tokenomics/dashboard?period=7d|30d|90d`
- `GET /api/admin/tokenomics/focus-records?period=7d|30d|90d&limit=1..100`

Explicit historical start/end filtering and native FOCUS event pagination remain
unsupported. These inputs are rejected before reading Engine; the interface must
explain the limitation rather than pretend to filter or fabricate billing rows.
[The TOK-1 runbook](../runbooks/TOK_1_BACKEND.md) owns current adapter evidence.

Server derives the authorized application/project/workspace scope. Reject client
scope overrides. Limit windows to 90 days, FOCUS pages to 100 rows and upstream
pagination to a documented bounded budget; signal partial/truncated results instead
of presenting them as totals. Handle expired Engine credentials, rate limits and
timeouts without leaking provider payloads or triggering inference. Page loads and
refreshes are read-only and do not generate model/embedding/audio calls.

Metric fields carry nullable value, unit, source, observation time, window,
coverage and basis (`observed`, `estimated`, `billed`, `unavailable`). Native
`unpriced_llm_calls` means cost coverage is incomplete even when total_cost is zero.
Prior Phase 8 evidence showed exactly this condition; do not convert it to free use.
The latest requester decision selects [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) as the price sources. This supersedes the earlier actual-cost-only acceptance requirement: observed usage multiplied by verified public tariffs may populate explicitly **estimated** cost views. It never becomes an actual or billed amount. Native unpriced zero remains unavailable as an actual cost. Keep separately reported actual/billed amounts distinct from estimates.

Version each price snapshot with retrieval time, source URL, exact model, currency, unit, service tier, context band and cache categories. Never guess an unknown model alias or missing price. Rates from these sources describe their respective provider APIs; gateway/cloud markups, private discounts, tax and historical tariff differences remain excluded or separately sourced. Apply per-request context bands, not the period-wide token sum. Cache reads/writes need measured attribution and provider-specific token semantics to avoid double counting.

Where only aggregate prompt/completion counts exist, an explicitly labeled standard-rate scenario may assume uncached regular input, standard service and no regional uplift. Surface those assumptions and missing cache/write coverage; do not claim a complete cost or upper bound. Do not allocate a multi-model total between input/output categories without supporting source data. Unknown models and unmeasured embedding/voice/tool usage remain unavailable. FOCUS-like BilledCost stays null without an actual billed source; estimates need their own field and basis.

TOK-0 must validate price provenance, formulas and coverage for the observed application usage, including missing providers/categories. An invoice/Admin Key is no longer a prerequisite for estimated-cost acceptance. A dashboard with no usable estimate or actual amount still does not satisfy the requested feature. No fixture fallback, invented usage, automatic provider call or shared pricing-policy mutation is authorized by this source decision.

Define before implementation:

- Total tokens: unique observed provider events, deduplicated by stable source ID;
  do not sum parent execution totals and their child spans again. If no reliable
  attribution/deduplication key exists, report the limitation rather than fabricate it.
- Average cost: same period, scope and pricing coverage as the execution denominator.
- Cache hit ratio: hits / eligible lookups for a named cache. Retrieval-cache hits
  differ from provider prompt-cache tokens; show separate metrics when available.
- Token goodput: tokens associated with completed successful executions / tokens
  with known execution outcome. Show attribution coverage; this is not answer quality.
- Empty denominators yield unavailable ratios, not NaN, infinity or a 100% default.
- Anomalies need a specified baseline/window/threshold and minimum sample size in
  TOK-0; missing baseline yields no fabricated anomaly. No extra model judge needed.
- FOCUS-like records preserve units; audio seconds, embedding tokens and language
  tokens cannot be added as if they were the same quantity. Unknown billed values
  stay null; do not relabel an estimate as an invoice amount.

Do not retrieve/store/display raw conversations, audio, secrets, user emails or
reasoning content to build these charts. Reuse existing recorded synthetic evidence
only in clearly labeled test fixtures. Live views must never silently fall back to it.
For the mymemory migration, record the cutover boundary and source provenance;
changing a memory cluster is not a new application or a reason to double-count usage.

## Phases and quality gates

| Phase | Deliverable | Required tests / acceptance |
| --- | --- | --- |
| TOK-0 — Data mapping | Inventory each reference metric against supported native sources; typed response contract; formulas, scope, limits and anomaly rule | Every metric mapped to a source or explicit unavailable state; observed/estimated/billed distinctions; fixture calculations for zero, missing, duplicates, partial coverage and mixed units |
| TOK-1 — Backend view | Admin-only bounded read endpoints and source adapters | user/unauthenticated denial, scope-override rejection, no secret/content leakage, deduplication, period filters, pagination, 429/timeouts/expired credentials, no inference on refresh; deterministic fixture tests |
| TOK-2 — Dashboards | Menu, six cards, Overview/Breakdown/FOCUS, charts, tables, filters and refresh | Every inventory section rendered; values match contract; zero bars and missing data correct; localized labels, keyboard/tooltips/table alternatives, mobile layout, preserved filters, loading/error/partial/empty states |
| TOK-3 — Integration | Existing admin navigation plus sanitized usage/price-source walkthrough; docs | End-to-end admin/user controls, no duplicate requests or uncontrolled polling, visual checks at 390/1440px and 200% zoom; estimated values reproduce observed usage × verified official rates for a bounded period with currency, assumptions and coverage recorded; any actual amounts retain their own provenance; missing prices never become zero or guessed rates; unavailable native metrics handled honestly; existing support/voice/knowledge regressions remain green |

Use UI-001 frontend/backend checks and record evidence after every change. Planned
commands/tests are not executed evidence. No production-capacity test, required
billing reconciliation or FOCUS certification is implied. No live provider API call,
new database, code implementation or dashboard rendering has occurred in planning.

## Delivery sequence

TOK-0 can proceed alongside UI-0 and MM-0. TOK-1 follows established admin API
boundaries; TOK-2 follows UI-1 and TOK-1. TOK-3 must pass before the expanded UI-4
final acceptance. Do not combine an Engine memory cutover with a dashboard rollout.
Changes ship in separate reviewable commits/PRs with evidence and quality-gated automatic publication authorized by the requester.

Use the shared I18N-001 catalogs for all chart labels, dates/numbers, tooltips, tables and error states. Never convert monetary currency when switching locale.


TOK-0 source mapping, read recovery and missing monetary coverage are recorded in [the data mapping runbook](../runbooks/TOK_0_DATA_MAPPING.md). The normalized contracts and 28 deterministic tests are implemented; the live backend adapter passed TOK-1 source acceptance; the dashboard UI remains TOK-2 work.


TOK-2 behavior and validation are recorded in [the dashboard runbook](../runbooks/TOK_2_DASHBOARDS.md).


[TOK-3](../runbooks/TOK_3_INTEGRATION.md) records the real source-to-screen acceptance and the remaining native capability gaps.
