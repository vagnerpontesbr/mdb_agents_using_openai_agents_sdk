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
