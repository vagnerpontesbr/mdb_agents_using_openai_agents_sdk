# Phase 2 journey: local preparation and hosted acceptance

Historical phase-specific evidence and versions follow. Use [Phase 7](PHASE_7.md)
for the active runtime and [publication status](REPOSITORY_SETUP.md) for current Git/CI.

**Status:** Phase 2 is complete for the bounded demo, including the user's final
browser audio confirmation. [Task evidence](../tasks/VERT-001-JOURNEY.md) records
actual checks and limitations; [ADR-0025](../adr/0025-phase-two-journey.md) defines
the contract. Commit `3c68530` is published with successful remote CI. The user subsequently
authorized Phase 3; [MEM-001](../tasks/MEM-001-MEMORY.md) records current work.

## Application startup

Follow [the application setup](APPLICATION.md) for frozen dependencies, private
Atlas configuration and built React assets. Keep the operator CLI login private
under ADR-0022. `APP_JOURNEY_ENABLED` defaults to `false`; accepted values are
exactly `true` or `false`. Enable it only after the hosted journey deployment and
native contract have passed acceptance. Inject `OPENAI_API_KEY` to enable voice.
No new application database collections or privileges are needed.

Protected API routes are `/api/capabilities`, `/api/journey/chat`,
`/api/journey/status`, `/api/journey/latest`, `/api/journey/review`,
`/api/voice/transcribe`, and `/api/voice/speak`. The chat endpoint emits progress
and a terminal SSE result, not live model tokens. The session token stays in the
HttpOnly cookie. Request bodies cannot choose Engine users, projects or workspaces.

The browser stores only an opaque conversation UUID in sessionStorage, keyed by
application user. “Check latest execution” reads the Engine session and restores
its latest result or pending action, not a chronological chat transcript. Stop
waiting affects browser waiting only; do not resubmit an uncertain action blindly.

## Prepare a credential-free hosted package

Use a new absolute temporary path for each stage:

```sh
python3 scripts/prepare_hosted_invoice.py \
  --output /tmp/telecom-phase2-new-stage \
  --profile journey \
  --python-archive /tmp/telecom-python315-linux-amd64.tar.gz \
  --compact-runtime
```

The script checks the existing pinned interpreter checksum, copies only the
allowlisted Python sources/manifests/lock, and selects
`openai_engine_adapter.journey:app`. It enables Engine memory and declares four
tools in the Tool Pod; agent egress stays denied. It does not upload or deploy.
The default invoice profile remains unchanged.

Accepted build `bld_01M6629HJ7T0QTMY1MG9CF1W8E` is deployed as
`deploy-926b87c0` (succeeded 2026-10-30T09:33:15.802Z). Uploaded source hashes are
recorded in [portable evidence](../../compatibility/phase2-journey-evidence.json).

## Authorized shared policy change

Read-only inspection on 2026-10-30 UTC confirmed `AUTHORIZED_TOOLS` contains 27
entries, including `lookup_invoice`, and none of the following additions:

- `telco_read_invoice`
- `telco_check_connection`
- `telco_offer_plan`
- `telco_simulate_plan_change`

The user approved adding exactly these four names to policy
`6ae1ab6186dc82d1c54886b1` in project `67b385a7976edf15ecc62e06`, retaining all current
entries. This policy applies to other project workspaces too, so the earlier
approval of `lookup_invoice` does not authorize this new shared expansion.
The workspace manifest limits this deployment to its four named tools.

`gpt-5.6-luna` is already authorized. Preserve the current 12 model calls,
12 tool calls, 80,000 tokens and 240,000 ms platform limits. No shared memory model,
secret, database grants, or unrelated deployment needs to change. SDK loop bounds
are tighter safeguards and do not replace these Engine policies.

The policy was re-read and updated from 27 to 31 tools; all other policies were
verified unchanged. Deployment `deploy-c4c7b79d` was started for the prepared build.
For future updates, re-read policy immediately before applying the union; never
replace a changed remote list with an old snapshot. Verify propagation before
positive probes and retain the previous values for a narrow rollback. Deploy only
the exact new build to `ws-6ae20f53f3b040aa65fa961a` (agentsdk). Prior accepted recall
build: `bld_01M63Y9G5090B560AYEFWA7D4K`; recorded restoration `deploy-9c637560`.
Verify exact deployment IDs because generic status has returned stale build data.

## Reproduce the accepted live controls

1. Build/deploy the staged artifact with frozen dependencies and inspect the exact
   build/deployment status. Keep other workspaces and shared memory configuration.
2. Invoke financial, technical, offer and mixed requests with synthetic users;
   verify actual model/tool trace correlation, returned user context in Tool Pod,
   bounded costs, exact templates and memory projection without duplicate writers.
3. Propose `fiber-500`; demonstrate suspension before any simulation activity,
   approve/reject, restart/replay, expired review and stale-generation denial.
   The tested `/executions/{id}/resume` path pins `suspend_generation` and records
   a JSON `human_review` envelope. `recorded_review_decision` strictly translates
   it to the domain answer. Do not replace it with an unpinned approval path.
4. Exercise another user/admin, forged parameters, same-session concurrency,
   provider/tool failure and uncertain transport recovery. Verify execution scope
   and native replay independently of the deterministic local receipt function.
5. Serve the built UI with real Atlas identity and the accepted journey deployment.
   Validate microphone capture, reviewed transcript, shared chat path and playback
   in a quiet environment. Prior Phase 0 microphone acceptance is not acceptance
   of this new complete journey.
6. Record sanitized evidence and remaining limits, run final local checks, and stop
   at the Phase 2 checkpoint with manual Git commands. Do not advance to Phase 3.

## Browser audio and session capacity

The API sets `media-src 'self' blob:` so the browser can play the synthesized WAV
from its local object URL. Other CSP directives remain restrictive. Reload a page
after changing response-header policy, then use **Check latest execution** to
recover the native result and **Play response** to listen again. The user accepted
the quiet-room audio retest on 2026-10-30.

The live acceptance app is available at http://127.0.0.1:53183 while its local
process is running. The persisted configuration still defaults the journey off;
set `APP_JOURNEY_ENABLED=true`, `APP_ORIGIN` to the exact chosen loopback port and
`APP_WEB_DIST=apps/web/dist` when starting it again. Existing Atlas users are reused.

Completed Engine sessions can retain sandbox reservations. The live matrix hit
`POOL_EXHAUSTED`; stopping only completed synthetic runtime sessions released the
reservations while preserving history. Inspect workspace runtime sessions and
stop only sessions you own and intend to end. Do not indiscriminately terminate
other demo sessions or increase shared platform limits to hide capacity failures.
