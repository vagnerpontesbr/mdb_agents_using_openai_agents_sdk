# UI-4: integrated demo handoff

## Scope and acceptance

The approved interface cycle includes profile editing/photo/password, admin Control
Plane settings, multilingual journeys and Tokenomics. UI-4 consolidates the accepted
scope without changing application code, Atlas, hosted agents or existing servers.
Its source baseline is integrated PR #19, `4b21bd64c08349bd717a35dfb65cb8f9e4f67972`.
[UI-001](../tasks/UI-001-PROFILES-CONTROL-PLANE.md) owns requirements.

| Boundary | Accepted evidence | Limits |
| --- | --- | --- |
| User/admin navigation, profile and password | [UI-001](../tasks/UI-001-PROFILES-CONTROL-PLANE.md), PRs #5–9; backend denial and browser/session tests | Upgrade all identity-serving processes before enabling password changes; retain credential-version checks on rollback |
| Application limits and cache | [UI-3](UI_3_CONTROL_PLANE.md), PR #15; authorized real persistence, revision conflict and denial checks | Subsequent operations only; settings restored to defaults at revision 3; no restart controls |
| Text, retrieval and voice languages | [Multilingual](MULTILINGUAL.md), [LANG-3](LANG_3_VOICE.md), PRs #10–14 | Accepted incomplete nine-case voice matrix, quiet-environment and source-language limits remain |
| Usage and estimated costs | [TOK-0](TOK_0_DATA_MAPPING.md), [TOK-1](TOK_1_BACKEND.md), [TOK-2](TOK_2_DASHBOARDS.md), [TOK-3](TOK_3_INTEGRATION.md), PRs #16–19 | Explicit estimates, partial coverage, trailing 7/30/90 days accepted by requester |
| Layout and accessibility | UI-001 and TOK-2/3 evidence: 390px/1440px, keyboard/focus and 200% zoom checks | Focused browser/visual acceptance, not a comprehensive accessibility certification |
| Cross-feature continuity | TOK-3 final 36-test browser suite; one held support execution survives navigation, period and locale changes | No new live provider invocation in the handoff |
| Real source-to-screen | TOK-3: exactly two usage GETs, 259,874 tokens, USD 0.0811888 estimated; three locales; 401/403 and scope rejection | Synthetic app identities with real aggregate usage; no billed reconciliation |
| Clean-source startup | [Sanitized evidence](../../compatibility/ui4-clean-start-evidence.json); frozen install, static build, synthetic login/reload/logout, explicit unconfigured Tokenomics | Package caches reused; no private environment, Atlas or Engine connection |

## Clean-source commands and results

Created `/tmp/telecom-ui4-clean.cOdOFM` from a Git archive of the source baseline,
without `.env`, `.venv` or `node_modules`. Used Python **3.15.2**, Node **26.5.0**
and npm **11.17.0**. This is a clean source/dependency-directory proof, not a
cache-free installation or production deployment.

Executed:

- `uv sync --project /tmp/telecom-ui4-clean.cOdOFM --frozen --python /Users/vagnerpontes/Documents/SDD/openai_agents_sdk/.venv/bin/python3`: passed, 59 packages.
- Initial `npm --prefix /tmp/telecom-ui4-clean.cOdOFM/apps/web ci`: failed with EUSAGE, `Missing: web@0.1.0 from lock file`. The following build failed with `tsc: command not found` because installation had failed. Manifests matched; the exact cause of the absolute-prefix behavior remains unconfirmed.
- `npm ci` from `/private/tmp/telecom-ui4-clean.cOdOFM/apps/web`: passed, 139 packages, without lockfile edits. `npm run build` there passed. README/APPLICATION now use this direct-directory sequence, matching CI.
- `npm audit --omit=dev --json`: zero runtime vulnerabilities. Full `npm audit --json`: ten moderate development-only advisories in the transitive lint chain from minimatch GHSA-g3hv-75wg-m249. This existing [Phase 6 limitation](PHASE_6.md) remains open for compatible remediation; the suggested forced ESLint downgrade was not applied.
- `TELECOM_TEST_PORT=53194 uv run --frozen python -m tests.foundation.browser_server` from the clean source, followed by `node /tmp/telecom_ui4_clean.cjs`: passed HTTP health/static UI, synthetic login/reload/logout and explicit 503 `tokenomics_not_configured` without losing login. No provider inference or Atlas mutation occurred.
- The isolated server was stopped; graceful application shutdown and process exit were confirmed. Existing demo servers were untouched.

The operator helper and screenshots are temporary artifacts, not packaged fixtures.
The sanitized JSON preserves the source commit, environment and outcomes.
For configured application startup follow [APPLICATION](APPLICATION.md) and its
linked private feature configuration. No automatic bootstrap, identity reset,
shared Atlas migration or live server restart is part of this handoff.

## Publication and verification

Baseline TOK-3 source `c6264803e4ec7e72bb0688e74e3b877b9e7eb184` passed both jobs in
runs [41376342124](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41376342124)
and [41376347743](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41376347743),
then merged in PR #19. UI-4 publication is pending until its exact source passes CI;
its PR will record the final head and run links. Local documentation validation passed:
`python3 scripts/check_repository.py` (102 Markdown files, 34 ADRs) and `git diff --check` (no whitespace errors). No full application
suite is claimed as newly executed locally for this documentation-only phase.
Required remote CI runs repository/compatibility/identity checks, backend lint/types/
tests/build, pinned hosted contracts, and frontend lint/types/unit/build/browser tests.

## Remaining work and rollout boundary

[MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md) is separate and unexecuted. Shared
project impact and supported Engine migration must be established before requesting
approval for an exact live switch. Engine retains sole managed-memory ownership.

Native billing/FOCUS records, historical custom ranges and other unavailable native
metrics remain unsupported; see TOK-3. Pricing sources are the requester-selected
OpenAI and Anthropic pages, but only the observed exact OpenAI model has a packaged
reviewed rate. No Anthropic usage or missing prices are invented. Estimated costs
exclude unreported fees and services and do not certify actual charges.

Merge does not deploy. Preserve the documented private activation and credential-version
rollout requirements. Existing accepted demo limitations and the USD 30 provider
ceiling are unchanged; this phase incurred no new inference calls.
