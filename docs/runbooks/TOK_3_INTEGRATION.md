# TOK-3: source-to-screen integration

## Result and scope

The supported Tokenomics path passed live source-to-screen acceptance: existing
Telecom Engine usage → bounded backend → localized admin UI. This is an isolated
loopback acceptance, not a deployment to the existing demo servers. Public-price
estimates retain their provenance, assumptions and partial coverage. [TOK-001](../tasks/TOK-001-TOKENOMICS.md)
owns scope; historical ranges and unreported metrics remain unsupported as documented.

## Bounded real-source walkthrough

Prepared an operator-only helper `/tmp/telecom_tok3_server.py` serving the actual
application on port 53193 with in-memory synthetic admin/user sessions and a counted
real Engine usage adapter. No Atlas identity data or business document was read or
written. Native Engine CLI status refreshed the existing private operator session.
No CLI invocation, model, embedding or audio call was performed.

The first helper launch failed before binding the server or reading Engine because
Python could not import repository test fixtures from `/tmp` (`ModuleNotFoundError:
tests`). Added the repository root to that helper's import path and restarted; server
startup then passed. This was a test-harness path failure, not a product regression.

Executed `node /tmp/telecom_tok3_browser.cjs` from apps/web against Chromium and the
isolated backend. The helper performed exactly **two** native usage GETs: initial
load and explicit Refresh. Successful checks:

- Unauthenticated API read returns 401; ordinary user dashboard/FOCUS reads return
  403; user UI shows Access denied; no upstream read occurs for these attempts.
- Admin source/API totals agree: **259,874 tokens**, public-price estimate
  **USD 0.0811888**, estimated basis and partial coverage. The observed prompt/output
  totals reproduce the official standard scenario. No value is relabeled as billed.
- The exact same amount renders with en-US, pt-BR and es-ES formatting. Locale
  changes are real profile updates on the isolated in-memory identity store;
  no extra Engine request occurs. There is no currency conversion.
- 390px and 1440px layouts and CSS zoom 2 pass page-width and one-line monetary-value
  checks. Visual inspection of the real-source pt-BR desktop capture confirms the
  source total, estimate, five UTC daily buckets and unavailable metrics are legible.
- FOCUS tab performs no additional source read and explicitly reports missing native
  invoice/SKU records. Workspace override and historical start/end queries return
  400 before source read. Historical range error uses its explicit unsupported code.
- Explicit Refresh produces exactly one additional source read and retains FOCUS.

[Sanitized evidence](../../compatibility/tok3-live-evidence.json) contains only aggregate
usage, estimate, source URL, coverage and check outcomes. Operator helpers/cookies and
screenshots remain outside the repository. Screenshots use synthetic application
identities, not real user profiles. The isolated server was stopped with graceful
shutdown confirmed; existing demo servers were not restarted or changed.

## Conversation continuity and deterministic regression

Added `Tokenomics filters and locale changes preserve the active support execution`
to the browser suite. It holds one synthetic support invocation, navigates to the
new dashboard, changes period, switches locale to pt-BR, and then returns to Support.
The original response and conversation ID are preserved, with exactly one invocation
and two explicit dashboard reads. No synthetic response is used by production code.

Executed `npm --prefix apps/web run lint` and `npm --prefix apps/web run typecheck`:
both passed. Focused Playwright command with `--grep 'Tokenomics filters'` passed one
test. The prior integrated TOK-2 gate passed all 35 browser tests and 11 frontend unit
tests, plus backend/hosted checks in remote CI. Full final regression and publication
results are recorded below; planned checks are not counted as executed.

## Remaining supported-source limits

Only 7/30/90 trailing presets are supported. Arbitrary historical date filtering is
still an unfulfilled source capability; no native contract proves exact historical
boundaries. Do not describe the full original date-filter request as implemented.
Native FOCUS invoices/SKUs, execution denominator, cache lookup ratio, token goodput,
context/agent/intent attribution and comparable anomaly baselines are unavailable.
The dashboard renders each missing section explicitly, as required by TOK-001.

Only the exact observed OpenAI model has a reviewed packaged rate; Anthropic's source
is approved, but no corresponding live usage was observed. Cache reads/writes,
embedding/voice/tool costs, gateway fees, discounts, taxes and historical price
changes are excluded from the standard estimate. No billed-cost reconciliation or
production capacity claim is made. The full expanded UI-4 gate must retain these
limitations; a new native source or explicit scope decision is needed for arbitrary
historical filters. Memory migration remains a separate phase.

Final local regression command `TELECOM_TEST_PORT=53189 npm --prefix apps/web run test:e2e`
passed **36 tests**. No new browser assertion failed in TOK-3. Repository/diff checks
passed (101 Markdown files / 34 ADRs). The only TOK-3 failure was the corrected
operator-helper import path before any source access. Local/backend unit suites were
not unnecessarily repeated for this test/evidence-only phase; required remote CI
repeats all suites. The supported integration proof is ready for publication.

The requester has been asked to decide whether trailing 7/30/90 presets satisfy the
demo scope or arbitrary historical filters remain a blocking requirement. Until an
explicit answer, do not mark the expanded UI-4 acceptance complete or silently waive
that requested behavior. Other native unavailable metrics retain their documented
unavailable-state treatment under TOK-001.
