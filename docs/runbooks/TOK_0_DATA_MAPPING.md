# TOK-0: source mapping and compatibility gate

## Status

TOK-0 merged in PR #16 as `3fc274c`; local and remote gates passed. Native usage reads work.
The requester has superseded the historical
actual-cost-only gate with official-price estimates. Local and remote contract gates passed. No TOK-1 adapter or
live dashboard is delivered. The `tokenomics.py` contracts are integrated. [TOK-001](../tasks/TOK-001-TOKENOMICS.md) owns acceptance.

## Native contract inspected

Official OpenAPI: https://www.mongodb.com/docs/api/doc/agentengine.json,
version `2026-09-20-preview`; hash in
[source evidence](../../compatibility/tok0-source-evidence.json).
GET `/api/v1/projects/{id}/cost/dashboard` accepts `period` and `workspace_id`.
Always select the configured Telecom project/workspace; do not query project-wide
aggregates to work around a workspace failure. Reads generate no inference.

| Requested metric | Native candidate | Remaining limitation |
| --- | --- | --- |
| Total cost | summary.total_cost_usd | Actual versus estimated semantics and coverage must be verified; unpriced_llm_calls prevents treating zero as free usage |
| Observed tokens | summary.total_tokens, total_prompt_tokens, total_completion_tokens | Native aggregation/deduplication semantics require verification; never add summary and breakdowns |
| Average cost per execution | No complete source identified | total_llm_calls is not execution count; need matching outcome/coverage denominator |
| Cache hit ratio | No field in cost response | Retrieval cache and prompt cache are distinct; unavailable |
| Token goodput | No outcome attribution in cost response | Unavailable without measured token/outcome association |
| Execution count | No field in cost response | LLM call count cannot substitute for executions |
| Application/workspace bars | by_workspace | Filter must demonstrably restrict the configured workspace |
| Daily cost/token bars | daily_trend | Missing days are gaps, not zero; explicit date boundaries not exposed in this contract |
| Anomalies | Derived daily observations | Require seven complete comparable UTC days and a positive mean; flag current day only after completion when above twice that mean; otherwise insufficient data |
| Context categories | No measured attribution in response | Unavailable; do not infer instructions, memory, RAG or reasoning shares |
| Token categories | Prompt/completion totals | Cached-input and overlap semantics unverified |
| Model bars | by_model | Model identity reported; embedding/voice coverage and type unverified |
| Agent/intent breakdown | No fields in cost response | Unavailable; do not distribute totals heuristically |
| FOCUS records | No event/SKU/billed-cost records in response | Aggregated cost is not a billed charge; no supported pagination or billing source identified |

No independent embedding, voice or direct-OpenAI actual-cost source has been
validated. A provider-calculated estimate cannot satisfy actual-cost acceptance.
No currency conversion or fixture fallback is allowed. The later source decision
below now authorizes explicitly labeled price-table estimates.

## Historical read-only retry after login renewal

Executed `python3 /tmp/telecom_tok0_read.py`: one GET for period `7d`, exact configured
workspace, preview Accept header, no redirects and a bounded response. The first
sandbox attempt failed to connect. The explicitly permission-enabled retry reached
the service and returned HTTP **500**. No response body, token or private URI was
retained. This is an upstream HTTP failure, not an application test failure; its
internal cause remains unknown. The prior failed attempt is preserved in evidence.
No model, embedding, audio, Atlas mutation or deployment occurred.

The login renewal has not resolved this compatibility gate. Next action needs a
working native endpoint or an accessible actual monetary source with application
scope, period, currency, provenance and coverage. Do not claim TOK-0 complete or
proceed to publish a dashboard whose entire cost source is unavailable.


## Historical investigation after Atlas resume — 2026-11-02 UTC

Read-only `atlas clusters list --projectId ... --output json` confirmed both
OpenAI-SDK and ClusterDemoTelco have `paused=false`, `stateName=IDLE`.
This is control-plane status, not a database query or proof of the prior 500 cause.

The first new `python3 /tmp/telecom_tok0_read.py` returned **401**. Although
`agentengine auth status` displayed a signed-in identity, a private JWT expiration
check confirmed the access token had expired. Running `agentengine status` with
the explicit existing Telecom target, `--json --no-log`, succeeded and natively
renewed credentials. No manual credential replacement or new login was needed.
The next cost GET returned **200**, and a confirmation GET returned the same totals.

The helper initially labeled the first 200 response unsuccessful because it required
`success=true`. The response omits this optional OpenAPI field. Corrected the helper
to distinguish absent from explicit false; the confirmation read passed. This was
a diagnostic classification bug, not a failed native response or application change.

Observed period `7d`, exact configured workspace verified in the single workspace row:

- 259,874 total tokens = 230,660 prompt + 29,214 completion tokens.
- 280 LLM calls, all 280 unpriced; reported model `gpt-5.6-luna`.
- One model row, one workspace row, five daily rows.
- Raw `total_cost_usd=0` is NOT accepted as actual zero cost: priced-call coverage is 0%.

The prior 500 is no longer reproduced after cluster resume and credential refresh;
these observations do not isolate its internal root cause. Connectivity recovery
is complete, while actual monetary acceptance remains blocked. The inspected native
OpenAPI exposes no additional pricing/billing read endpoint to resolve the missing
amounts. No shared pricing configuration was changed. Need an accessible actual-cost
source for the configured application, or native source remediation, before cost
acceptance. Embedding and voice monetary coverage remain unverified.

Validation: `python3 scripts/check_repository.py` and `git diff --check` passed after
this evidence update. Application suites were not run: this investigation changes
only documentation/evidence; the pre-existing contract draft remains unvalidated.
No new inference, database mutation, deployment, commit or PR is claimed here.


## Requester-selected pricing sources — current decision

The requester selected the official OpenAI and Anthropic pricing pages. This resolves
the source decision for **estimated** costs and supersedes the historical requirement
for actual-only acceptance above. [TOK-001](../tasks/TOK-001-TOKENOMICS.md) owns the
updated semantics; no further invoice-access confirmation is required for estimates.

Both pages were fetched and read. [Pricing snapshot](../../compatibility/tok0-pricing-sources.json)
records URLs, retrieval date, the observed OpenAI model rates and a reproducible
calculation. For `gpt-5.6-luna`, standard short-context USD rates per million tokens
are input 0.20, output 1.20, cached input 0.02, 30-minute write 0.25 and 12-hour write
0.50. Long-context prices differ; context threshold is 272K input tokens per request.
Anthropic's page separately identifies input/output, 5-minute/1-hour writes and cache
hits, with model-specific rates and context/tier/geography modifiers. No Anthropic
usage was observed in the scoped response; source approval does not fabricate it.

For the recorded seven-day sample, the explicit uncached-standard scenario is
`(230660 × 0.20 + 29214 × 1.20) / 1000000 = USD 0.0811888`.
This is a public-price estimate, not an invoice or a complete measured cost. Cache
reads/writes and service tier are not exposed by this aggregate; gateway charges,
discounts, taxes, voice, embeddings and tool fees are excluded. Current prices are
applied retrospectively, without proof of historical tariff effectiveness. It is
not a guaranteed upper bound. Do not use the same input/output split for multiple
models: this example is valid as a scenario only because exactly one model is reported.

No runtime adapter or dashboard has been added in this source-selection update.
At that source-selection boundary the contract was unvalidated. The subsequent
contract gate below records completed local validation.

## TOK-0 contract gate

Implemented normalized `Metric`, bounded timezone-aware `Window`, complete dashboard
section inventory and separate FOCUS billed/estimated contracts. Unknown sections
require reasons; incomplete KPI/section coverage cannot masquerade as complete.
Decimal arithmetic preserves small monetary amounts. Leaf event aggregation rejects
mixed units/currencies/sources/scopes/windows and conflicting duplicate IDs, deduplicates
identical IDs, and returns a labeled subtotal for missing coverage. Ratios cannot be
summed. The adapter remains responsible for proving disjoint leaf identity; native
summary/breakdown totals must never be added together.

`Price` binds exact model/provider to the requester-selected official URL, retrieval
time, context band and standard tier. `standard_scenario` requires nonnegative integer
usage, rejects model alias substitution, and always returns estimated basis with
assumptions. It is a pure calculation, not live pricing discovery. The reviewed JSON
snapshot remains evidence, never an automatic fallback for missing native usage.

Remaining adapter constraints for TOK-1:

- One scoped native dashboard GET per refresh; 30-second timeout, 1 MB response cap,
  no inference and no automatic retry. Native endpoint has no pagination contract.
- At most 100 rows per normalized section/FOCUS page and 90 days per request. Reject
  oversized source responses explicitly; do not silently present truncated totals.
- Native `period` presets are known; explicit historical date-range filtering is not
  yet supported by evidence. Return unsupported-range/unavailable state unless exact
  matching native filtering or sufficient day/model/category attribution is verified.
  Never prorate period-wide cost or allocate token categories heuristically.
- FOCUS event/SKU/billed records remain unavailable; do not manufacture invoices from
  model aggregates. Anomalies need seven consecutive complete comparable UTC days,
  the same metric/basis/currency, and a complete current day. The arithmetic helper
  assumes the adapter has established those preconditions.
- Private CLI auth status alone does not prove token freshness. Native CLI status
  successfully refreshed the session during this investigation. Design bounded auth
  handling without exposing tokens or invoking the model.

Local checks: 28 Tokenomics tests passed; mypy passed (32 modules). Initial Ruff
reported import order (auto-corrected) and one overlong line (manually corrected).
The first three uv checks could not access the sandboxed cache and did not run;
permission-enabled retries ran successfully except for that corrected Ruff line.
No behavioral assertion failed. Full regression and publication evidence follow.

Final local gate: `uv run --frozen pytest -q` passed **277 tests**, including the
28 new Tokenomics cases; `uv run --frozen ruff check src/telecom_app tests/foundation`
passed after the corrections above; `uv run --frozen mypy` passed 32 modules;
`uv build --no-build-isolation` produced wheel/sdist. `python3 scripts/check_repository.py`
passed 98 Markdown files / 34 ADRs; `git diff --check` passed. Local frontend,
hosted-contract and identity suites were not rerun for this pure-contract change;
the required repository/application CI runs them before merge. No new live read,
provider call, deployment or Atlas mutation occurred during the contract gate.

Review: no primary trace/memory owner or live endpoint was added. No raw conversations,
credentials, private URIs or usage fallback is introduced. The user-selected tariff
scenario intentionally remains incomplete and cannot populate FOCUS billed cost.
TOK-0 local acceptance is complete; remote CI is the publication gate. TOK-1 owns
supported native adapters and admin authorization; TOK-2 owns interface rendering.


## Remote gate and integration

Source `d0fdf2e5d4a4e3b08c8f76ae49ceb3fb4947624a` passed repository/application jobs
in runs [41370855873](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41370855873)
and [41370868236](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41370868236).
The PR run passed 75 compatibility, 15 identity, 277 foundation, 96 hosted-contract,
6 frontend unit and 29 browser tests, plus lint/types/build/package checks. No remote
behavioral failure occurred. Log/status retrieval encountered a sandbox network
failure; permission-enabled retries succeeded. PR #16 merged as `3fc274c`.
TOK-1 branch `codex/tok-1-backend` starts from that integrated main. This integration
record is authored on the successor branch; no TOK-1 endpoint or deployment is yet claimed.
