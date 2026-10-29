# Running the Phase 0 demo

This runbook operates the bounded Phase 0 compatibility UI. The separate
[Phase 1 React account application](APPLICATION.md) has its own startup commands. Read the [Phase 0 checkpoint](../compatibility/PHASE_0.md) for accepted
scope and [dependency environments](../tasks/COMP-001-DEPENDENCIES.md) for setup.
Commands below assume the existing frozen agent-runtime environment and its
pinned Python 3.15.2 interpreter. Do not silently downgrade that target.

## Private configuration and identities

Inject configuration through the ignored root `.env`, using `.env.example` as the
key reference. Never commit `.env` or paste credentials into reports.

- `APP_MONGODB_URI` and matching `APP_MONGODB_HOST` target OpenAI-SDK. The validated
  demo user is `telecom_demo_identity_runtime`, restricted to that cluster and the
  three `telecom_identity` collections. [COMP-005](../tasks/COMP-005-DEMO-AUTH.md#restricted-application-identity-passes)
  owns the exact permission specification and evidence.
- `OPENAI_API_KEY` is required by the separate voice probe. The hosted model uses
  its existing workspace-injected credential, not a browser-provided key.
- The backend privately reuses the operator's Engine CLI login. App users do not
  log into Engine or receive its token. See [ADR-0022](../adr/0022-demo-private-engine-cli-identity.md).
- The initial app administrator is `admin@mongodb.com`; its password is not stored
  in this documentation. Bootstrap is insert-only and uses a hidden prompt. The
  existing administrator must not be reset by rerunning bootstrap.

Atlas CLI authentication is for administrative role/user provisioning. Engine
CLI authentication is separate. Expiry of one session does not imply the other
was refreshed. Renew through the relevant CLI's documented login flow; do not
copy tokens into the browser or change shared identities to repair a local login.

## Login, user registration and native invoice review

From the repository root:

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/serve_demo_auth.py --port 52774 --engine-review
```

Open `http://127.0.0.1:52774`. Log in as an existing app user. Administrators can
register `user` or `admin` accounts; ordinary users cannot register accounts.
Request the synthetic invoice, inspect the pending native Engine action and
approve/reject as its original requester. Another administrator cannot approve
someone else's action. Log out when done. The server binds loopback only.

The running hosted demo was last restored to `recall_invoice:app`, build
`bld_01M63Y9G5090B560AYEFWA7D4K`, deployment `deploy-9c637560`.
[Failure/restoration evidence](../../compatibility/hosted-dependency-failure-evidence.json)
records the subsequent successful native approval and memory recall. This is a
recorded checkpoint, not a perpetual health assertion.

## Microphone, speech output and chat continuation

Use a quiet environment and only the displayed synthetic English phrase:

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/serve_voice_engine_probe.py --allow-live --microphone --port 52775 --output artifacts/compatibility/microphone-latest.json
```

Open `http://127.0.0.1:52775`, click **Start microphone test**, allow the microphone,
and wait for **Recording**. Say:

> Read invoice demo one and recall my synthetic verification marker.

Click **Finish recording**, then **Play approved response** when enabled. Report
whether the complete response was intelligible. Capture is capped at 15 seconds.
Audio stays in local process/browser memory and is sent to OpenAI for transcription;
Engine receives the text. No raw audio/transcript is saved in the evidence report.

This diagnostic uses one fixed synthetic Engine user and automatically approves
only its exact synthetic fixture. It is separate from the authenticated app UI
and is not proof of a production authenticated voice gateway. Both channels recall
an existing marker; this is not a new-fact extraction-quality experiment.

Unrecognized speech returns 422 with an explanation and permits a bounded manual
retry before Engine work. At most three submissions are allowed per process.
Closing the browser or stopping playback does not cancel accepted remote work.
A provider/Engine failure can leave an uncertain outcome: inspect evidence before
retrying. Restart the one-shot probe deliberately for a new completed test, and
reload the page after restarting so it receives the new request nonce. Never
label an old report as evidence of a new attempt.

## Evidence, checks and next phase

The [voice task](../tasks/COMP-004-VOICE.md), [identity task](../tasks/COMP-005-DEMO-AUTH.md),
and [fault task](../tasks/COMP-003-FAULTS.md) retain successes, failed attempts and
reproduction commands. Reports contain synthetic correlation metadata, not keys,
passwords or customer records. Use a new ignored artifact path for new experiments
instead of overwriting committed evidence.

See [CONTRIBUTING](../../CONTRIBUTING.md) for deterministic tests. Live provider
probes require explicit live flags where implemented and incur usage; do not
re-run them just to verify documentation. Phase 1 is not started by these commands.
