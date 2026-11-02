# TOK-2: localized Control Plane dashboards

## Delivered behavior

The admin Tokenomics route renders all six KPIs and Overview, Breakdown and FOCUS
tabs. Native usage, public-price estimates, zero and unavailable values remain distinct.
Amounts retain USD; locale changes formatting without currency conversion. Tiny
nonzero monetary values use scientific notation instead of rounding to zero.

Overview includes workspace bars/table, daily UTC columns/table and an explicit
insufficient-baseline anomaly section. Breakdown includes all eight context categories,
token categories, model, agent and business-category sections, including unavailable
tables. FOCUS has period/provider/SKU/quantity/unit/billed/estimated columns and the
native unavailable state; no fabricated billing records or pagination controls.
The route never claims FOCUS certification. Source limitations remain owned by
[TOK-1](TOK_1_BACKEND.md) and [TOK-001](../tasks/TOK-001-TOKENOMICS.md).

7/30/90-day filters apply through the backend. Filters and active tab live in the
authenticated workspace, surviving tab switches, refresh and navigation away/back;
logout discards them. Arbitrary historical date ranges display a clear unsupported
explanation rather than a nonfunctional date picker. No hidden range approximation.

Each refresh makes one dashboard request and one FOCUS request (which performs no
native source read). Tab changes and locale formatting trigger no new requests.
An in-flight promise is reused for StrictMode effect subscriptions. Busy controls
prevent overlapping user refreshes; cleanup ignores late results. No polling or
automatic retry is added. The support journey retains its existing mounted owner.

The typed frontend boundary validates finite decimal strings, KPI units, scope/window
consistency, section counts/identities, estimated-price provenance and separate billed
cost semantics. Malformed responses clear the view. Safe Tokenomics-specific messages
replace generic account errors; native auth expiry does not sign out the application.

## Accessibility and visual behavior

All labels/statuses/explanations are in en-US, pt-BR and es-ES catalogs. Source model
identifiers and UTC day labels remain source identifiers. The observed/requested
window timestamps use the profile timezone. Daily data is explicitly labeled UTC.

Six responsive cards expose basis, units, coverage and source details through native
keyboard-operable details/summary controls. Tabs implement arrows/Home/End, roving
focus, selected state and labeled tabpanels. Charts are decorative complements to
accessible labeled tables. Zero bars/columns have exactly zero width/height, missing
values use an em dash and availability label. No decorative minimum bar length.
Narrow tables scroll inside keyboard-focusable regions; page layout never needs
horizontal scrolling. No new chart or router dependency is introduced.

## Validation and failures

`npm --prefix apps/web run lint`, `npm --prefix apps/web test` (11 tests), and
`npm --prefix apps/web run build` (TypeScript plus Vite) passed. New unit tests cover
small amounts, unavailable versus zero, malformed/nonfinite responses, untrusted
price URLs, billed/estimated separation, exact read requests and safe source errors.
Catalog key/placeholder parity remains covered.

New browser coverage: complete inventory, one request pair per refresh, preserved
filters/tab, keyboard tabs/details, zero bars, missing KPIs, error-data clearing,
normal-user route denial/no reads, and en/pt/es at 390px/1440px and CSS zoom 2.
CSS zoom is explicitly a simulated 200% reflow check, not browser-menu zoom.

Failures and corrections:

1. First focused run: 5 passed / 1 failed. `getByLabel('Period', exact)` did not resolve
   the nested select even though the accessibility tree showed combobox `Period`.
   Changed the test to `getByRole('combobox', {name:'Period', exact:true})`.
2. First full run: 33 passed / 2 failed. The inventory test used exact text for a
   list item containing both `Semantic memory` and `unavailable`; changed to its
   listitem with matching text. The older workspace test mocked identity without
   mocking the new Tokenomics API, so a real 401 correctly cleared its simulated
   session. Added explicit unavailable endpoint doubles to that navigation fixture;
   application authorization is unchanged.
3. Visual review found narrow table words broken across letters. Added a readable
   minimum table width with bounded internal scrolling, and corrected the English
   workspace label. Reviewed regenerated 390px pt-BR and 1440px en-US captures.

Screenshots are generated under ignored `apps/web/test-results` and use synthetic
identities/data. They are not production screenshots or proof of a live UI source.
Backend code/dependencies are unchanged in this phase; required CI repeats backend,
hosted, identity and frontend/browser suites. TOK-3 owns the live source-to-screen
walkthrough. No inference, Atlas mutation or production deployment is performed.

Final complete browser rerun passed **35 tests** after the fixture/selector fixes.
Command: `TELECOM_TEST_PORT=53189 npm --prefix apps/web run test:e2e`.
The same suite includes all existing support/voice/profile/knowledge regressions.

Additional visual review found that the 200% CSS zoom image had no page overflow but
still squeezed monetary digits into several lines. Changed card columns to fit the
available container width and added a one-line monetary-text assertion at zoom in
all three locale cases. The final build passed; the focused three-locale reflow
rerun is recorded below. This visual correction does not erase the earlier finding.

The focused rerun `TELECOM_TEST_PORT=53189 npm --prefix apps/web run test:e2e -- --grep 'localized desktop/mobile'`
passed all **3 locale cases** with the new one-line amount assertion. Visual inspection
of the regenerated Spanish zoom image confirms readable card amounts and bounded
tables. Final lint passed. Repository/diff checks passed (100 Markdown files, 34 ADRs).
Local TOK-2 acceptance is complete; publication/required remote CI remain pending.


## Remote gate and integration

Source `955cadec0befbc2086b0b74f6f92b87cdb6e9fa3` passed repository/application CI in
runs [41375051481](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41375051481)
and [41375135325](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41375135325).
No remote checks failed. PR #18 merged as `44e69a4c2011e2b27b51ad90d84b627f77f44611`.
TOK-3 branches from that main and owns the isolated real-source walkthrough.
