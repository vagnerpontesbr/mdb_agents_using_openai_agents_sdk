# Repository publication and CI status

Remote: https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk

## Current publication and work checkpoint

Phase 2 is published on `codex/phase-2-journey` as
`3c68530d932182b0fdba81319dc08a5a4dfb841d`. Its
[GitHub Actions run](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41036233739)
passed, verified on 2026-10-30. Phase 1 commit `b2ff9c7` also has successful remote CI.

The user authorized Phase 3 after that publication. [MEM-001](../tasks/MEM-001-MEMORY.md)
records its local changes and hosted evidence. Phase 3 has not been committed or
pushed; its new remote CI remains separate. The user performs Git publication
manually. Earlier checkpoints below are history.

## Verified Phase 0 publication checkpoint

On 2026-10-29, commit
[`43746c67e81203c52d18ee81626412eff73f652a`](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/commit/43746c67e81203c52d18ee81626412eff73f652a)
(`feat: complete phase 0 demo compatibility`) was committed and pushed on
`codex/repository-foundation` at the user's explicit request. `git ls-remote`
matched the local hash, and the working tree was clean immediately afterward.

[PR #1](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/pull/1)
integrates `codex/repository-foundation` into `main`. It was open with no
conflicts, reviews or comments at the pre-merge check. The user authorized
publication of this documentation and completion of the PR. Consult the PR
for its current merge state and checks; the evidence below is commit-specific.
This documentation reconciliation follows implementation commit `43746c6`.

## CI: correction published and both checks passed

The user committed and pushed the disconnect-test fix as
`60ef97b32d9fc4aea06554907c18872f0534a909`. Both GitHub Actions runs for that exact
commit completed successfully, verified through the GitHub API:

| Event | Run | Observed result |
| --- | --- | --- |
| Push | [40952249362](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40952249362) | Success |
| Pull request | [40952254396](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40952254396) | Success |

The earlier mixed results below belong to `43746c6` and are retained as history.

| Run | Observed result |
| --- | --- |
| [40950640625](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40950640625) | Completed successfully |
| [40950648966](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40950648966) | Failed in the compatibility suite |

The failed run reports `KeyError: 'client_delivery_lost'` in
`test_disconnect_preserves_completed_work_and_blocks_redispatch`, at
`tests/compatibility/test_voice_http_faults.py:147`. The test expected the delivery
flag to be present in its report. Inspection identified a synchronization race:
the shared completion event could be signaled by a fixture or duplicate request,
allowing the report to be read before the disconnected request finished saving
its delivery failure. The local fix tracks handler completion by client address
and waits for the exact disconnected connection. Real TCP reset, completed-work,
delivery-loss and single-dispatch assertions remain intact; production behavior
and the workflow are unchanged.

Local validation on 2026-10-29:

- Linux amd64, Python 3.15.2, image `telecom-recall-v1:local`, network disabled:
  100 consecutive disconnect-test executions passed; all workflow commands passed
  (repository check: 61 Markdown files/23 ADRs; 74 compatibility tests; 15 demo
  authentication/admission tests).
- macOS, frozen agent runtime: all 74 compatibility tests passed.

The fix is committed, pushed and validated on GitHub's runner by the two runs
above. The documentation reconciliation is a separate follow-up and requires
its own CI run; it is not included in `60ef97b`.

The [workflow](../../.github/workflows/repository-checks.yml) runs repository link/
structure checks, the compatibility suite and demo identity/admission tests. It
does not run hosted-contract tests, provider evaluations or deployments. Branch
protection, required checks and optional Codex review configuration remain
unverified; a workflow file does not establish those repository settings.

## Phase checkpoint and future Git work

[Phase 0](../compatibility/PHASE_0.md) records accepted bounded integration evidence,
including the restored hosted demo; it is distinct from PR/CI/merge acceptance.
Phase 1 was subsequently authorized; its acceptance is tracked separately. Default to preparing exact manual Git commands, unless
the user explicitly authorizes the assistant to execute commit/push. Preserve
remote history and use the repository review process; do not force-push or claim
unverified operations succeeded.

Earlier initialization/network/plugin-write failures were historical setup
constraints. They no longer describe the verified publication above. Do not
relocate Git metadata or retry plugin writes to bypass restrictions.

## PR #3 intermittent login-limit test correction

The PR #3 run `41038899374` failed because
`test_unknown_accounts_share_peer_rate_limit` used the real clock and crossed a
minute boundary: the ninth request correctly entered a fresh counter window and
returned 200 instead of the test's expected 429. The merge and Phase 3 commit
subsequently passed CI, but that did not remove the timing-dependent test defect.

The locally authored correction injects a fixed clock into this test, verifies
429 after eight unknown-account attempts, then advances one second across the
minute boundary and verifies successful login. Application rate limits and the
shared identity fixture remain unchanged. Seven HTTP tests and Ruff passed;
new remote CI requires the user's manual commit/push. Phase 4 work in progress is
separate from this correction.

## Verified Phase 4 publication

On 2026-10-30, local HEAD and the remote `codex/phase-2-journey` branch both
resolved to `1a52afce2815be3530d77cb7a714001f412ad206`
(`feat: complete phase 4 governed PDF knowledge`). The working tree was clean
before Phase 5 edits. Both repository and application jobs passed in
[run 41062532149](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41062532149).
The user performed publication; no merge is claimed. The preceding deterministic
login test correction `b9e641e` also passed CI in run `41040063310`.

## Phase 5 completion, Git publication pending

On 2026-10-31, bounded Phase 5 acceptance passed in
[EVAL-001](../tasks/EVAL-001-QUALITY.md). Workflow 8 is deployed as `deploy-af009ed4`
from build `bld_01M691YPABN60FEKHW6E1KZGB5`; eight final hosted invocations passed.
Local validation passed 128 backend tests, 86 hosted contracts, Ruff, mypy and
repository checks. HEAD is still `1a52afc` on `codex/phase-2-journey`; no Phase 5
commit, push, PR or CI run is claimed. The user performs Git publication manually.
After publication, verify the new remote commit and CI before starting Phase 6.

## Phase 5 publication verified

On 2026-10-31 local HEAD and remote `codex/phase-2-journey` both matched
`1a81be69cf0289f28b26def7e728c2c8f6d5619d`. Both jobs passed in
[CI run 41205974527](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41205974527).
This supersedes the preceding publication-pending note. The user authorized Phase 6
experience/packaging and selected MIT; [REL-001](../tasks/REL-001-HANDOFF.md) tracks it.

## Phase 6 completion, Git publication pending

The requester selected MIT and accepted the automated isolated handoff rehearsal on
2026-10-31. [REL-001](../tasks/REL-001-HANDOFF.md) records 130 backend tests, three
frontend unit tests, ten browser tests, frozen clean installation, builds, setup
diagnostics and tool adaptation. Phase 6 code/docs are uncommitted; no Phase 6 CI
or push is claimed. Phase 7 has not started.

## Phase 6 publication and CI correction

Phase 6 is published as `9b048bb`, with correction `a4f5c4c` and passing CI `41207242615`. Phase 7 runtime acceptance is complete for the bounded demo; its documentation/evidence awaits manual publication. Phase 8 scalability/resilience has not started.

[CI run 41206970479](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41206970479)
failed in `test_source_allowlist_and_existing_destination_rejection`: the staging
helper correctly included `LICENSE`, but the test expected only the previous files.
The correction preserves the strict allowlist and verifies exact license content.
All 75 compatibility tests passed locally with frozen Python dependencies and
local-port access. The user must commit/push the correction before remote CI
can be verified. This supersedes the preceding Phase 6 publication-pending note.

## Historical checkpoint — Phase 6 CI passed, Phase 7 complete locally

On 2026-10-31 the clean local branch and GitHub CI head matched
`a4f5c4c6c0903003f53903985a1218f7cab82e94`. Both jobs passed in
[run 41207242615](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41207242615).
This supersedes the preceding pending correction note.

[RUN-001](../tasks/RUN-001-RUNTIME.md) records fresh workflow 8 recovery, healthy
deployment and 86 local contract tests. Phase 7 documentation/evidence and the
decision reconciliation are local changes; no new commit, push or deployment is
claimed. Phase 8 remains pending and must wait for the manual publication gate.

## Phase 7 publication verified; Phase 8 in progress

Commit `610ca8babde73ae7fa61fdc97e24dc22ca233136` is published and both jobs passed
in [CI 41207595549](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41207595549).
The tree was clean before Phase 8 work. This supersedes the Phase 7 publication
pending note. [OPS-001](../tasks/OPS-001-RESILIENCE.md) contains locally authored
Phase 8 scripts, namespace controls and measured evidence. Phase 8 source changes
remain uncommitted and unpublished; no hosted redeployment is claimed. The approved
Atlas provisioning was completed as recorded below. Full acceptance is pending.

Phase 8 follow-up: the approved load resources were subsequently applied after
Atlas CLI login renewal. Role/index and bounded ingestion/cache checks passed;
see OPS-001. These remote Atlas changes are distinct from local source changes.
No Phase 8 commit/push or hosted redeployment has been performed.

Phase 8 bounded sustained, real Atlas read and speech-contention profiles subsequently passed. Local validation passed 138 backend and 86 hosted contract tests. The requester subsequently excluded production-capacity and pricing proof from acceptance, completing Phase 8 for the demo scope. No new Git/CI publication or hosted deployment is claimed. The measured reports and limitations are authoritative in OPS-001.
