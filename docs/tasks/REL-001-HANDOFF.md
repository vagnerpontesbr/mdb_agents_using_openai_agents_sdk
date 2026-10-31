# REL-001: Reproducible demo handoff

- Status: Completed for the bounded demo; requester accepted automated rehearsal on 2026-10-31; Git publication pending
- Owner: Telecom demo maintainer
- Dependencies: FND-003, VERT-001/002, MEM-001, RAG-001, EVAL-001
- Relevant ADRs: [ADR-0017](../adr/0017-two-cluster-memory-boundary.md), [ADR-0022](../adr/0022-demo-private-engine-cli-identity.md), [ADR-0027](../adr/0027-bounded-knowledge-evaluation-cache.md)

## Scope

Package the existing React/SDK/Engine demo for a new developer. Reconcile current
setup/configuration guidance, provide offline prerequisite checks and a reproducible
business-tool adaptation exercise. The user selected MIT on 2026-10-31. Phase 6 is
experience/packaging; load/resilience is Phase 8 and is not started here.

## Acceptance criteria

- One linked setup/demo/adaptation path identifies exact prerequisites and private config.
- A clean isolated checkout builds the backend/frontend and exercises the browser demo.
- Setup diagnostics never print credentials or contact providers.
- The tool adaptation trial rejects an obsolete price and preserves exact templates.
- Governance inspection and native approval boundaries are documented without inventing
  source validity, memory history or deployment independence.
- MIT license is present; original asset licensing does not relicense dependencies.
- Record actual automated rehearsal separately from an independent human handoff.

## Validation plan

Follow [the Phase 6 runbook](../runbooks/PHASE_6.md). Use a temporary checkout with
fresh dependency environments for the rehearsal. Run relevant deterministic tests,
package/build/browser checks and repository validation. No new credentials, policies,
indexes, live documents or provider spend are needed for packaging checks.

## Evidence and handoff

Phase 5 commit `1a81be69cf0289f28b26def7e728c2c8f6d5619d` matches the remote branch.
Both jobs passed in [CI run 41205974527](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41205974527). Phase 6 changes are local and uncommitted.


The [isolated rehearsal evidence](../../compatibility/phase6-handoff-evidence.json)
records a clean source checkout plus reviewed Phase 6 overlays, without `.env`,
`.venv` or `node_modules` copied from the development workspace. Frozen Python and
frontend installation passed; download/browser caches were shared. Python 3.15.2,
Node 26.5.0 and npm 11.17.0 were retained. Checks passed: 130 backend tests, three
frontend unit tests, ten Chromium browser tests, backend sdist/wheel, React build,
frontend lint, backend lint/types, setup diagnostics and tool adaptation. The MIT
license was verified inside the wheel and allowlisted hosted source stage.

The operator tool adaptation changed a synthetic price only in a temporary source
copy, verified the new quote, rejected the old price and checked the exact simulation
receipt. It did not alter the repository's business rules or call providers.
The browser walkthrough includes account controls, exact native-review presentation,
recovery and voice permission/playback behavior using doubles. It is not fresh live
provider acceptance; Phase 5's deployed evidence remains authoritative for that.

Dependency audit at rehearsal time found zero production dependency vulnerabilities
and ten moderate development dependency reports originating in minimatch through
lint tooling ([advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249)). No forced
ESLint downgrade or unvalidated lock change was applied. This is a recorded tooling
limitation, not a claim that dependency security is permanently established.

The initial plan asks for a new developer's handoff trial. The automated isolated
rehearsal is complete, but independent human acceptance has not been observed. The
user is being asked whether this rehearsal is sufficient for the demo's Phase 6
acceptance or whether to keep the human trial open. No Phase 7 work has started.


## Completion

On 2026-10-31 the requester explicitly accepted the automated isolated rehearsal
as sufficient for this demo's Phase 6 handoff. This is an accepted demo scope limit,
not evidence of an independent human trial. Phase 6 is complete: MIT selected and
packaged, current setup/configuration/docs reconciled, isolated setup/build/browser
and tool-adaptation rehearsal passed, and limitations recorded. Phase 6 files are
local and uncommitted; the user performs commit/push. Stop here before Phase 7.
