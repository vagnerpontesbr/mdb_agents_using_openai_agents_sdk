# COMP-004: Synthetic voice round trip and chat continuation

- Status: Bounded provider, hosted voice/chat and synthetic browser codec/playback proofs passed; microphone/human listening and broader channel controls pending
- Owner: Repository implementation
- Dependencies: COMP-001 locked agent environment, configured OpenAI access
- Relevant ADRs: [Shared voice workflow](../adr/0008-voice-channel.md), [controlled responses](../adr/0009-deterministic-responses.md)

## Scope and acceptance

Exercise the pinned Python VoicePipeline with a generated English request, real speech recognition, a structured agent result, backend-rendered speech, and a following text turn using the SDK's returned input items. Require the spoken code in both transcriptions, exact rendered response text, exactly one voice user item in the carried history, nonempty bounded PCM and the complete turn lifecycle. The following chat question does not contain the answer.

The diagnostic stores no audio or conversation transcript on disk and never writes Engine-managed memory. Its bounded ephemeral history is only an in-process compatibility test, not an application session adapter.

## Implementation and limits

[check_voice.py](../../scripts/check_voice.py) requires `--allow-live` and configured `OPENAI_API_KEY`/`OPENAI_MODEL` before importing provider dependencies. A child-process deadline bounds a full attempt to 150 seconds; the OpenAI client uses a 30-second transport timeout and zero retries. Successful execution makes six provider requests: fixture TTS, input STT, structured agent, response TTS, output STT and chat continuation. Input/output PCM is mono 24 kHz, 16-bit, limited to twenty seconds each. Tracing and raw SDK logs are disabled; failures suppress exception text. Killing a timed-out process does not cancel provider work already accepted or guarantee zero charges.

The model extracts a nullable support code. Python validates its format and renders the fixed response; schema conformance alone does not establish correctness, so the separate expected-code checks remain mandatory. A custom VoiceWorkflowBase is used because the installed SingleAgentVoiceWorkflow manages its own private history and exposes no Session argument. After the voice turn, `RunResult.to_input_list()` supplies the following chat request. This proves the public input-item continuation path only.

## Actual evidence

On 2026-10-28, a live run passed all seven checks at `2026-10-28T15:24:30.244808+00:00` on macOS ARM64, Python 3.15.2, openai-agents 0.24.0, openai 3.40.0 and numpy 2.5.4. The configured agent model was gpt-6-luna; audio models were gpt-4o-mini-transcribe and gpt-4o-mini-tts, using the alloy voice. Input audio was 4.7 seconds; output was 2.7 seconds. These durations are not latency measurements. The lifecycle was turn_started, turn_ended, session_ended. Safe local report: `artifacts/compatibility/voice.json`.

An earlier attempt failed with ValueError during the voice pipeline, with no detailed cause retained. The probe originally compared arbitrary model prose with an exact sentence; that fragile check was replaced by structured extraction and backend rendering before the passing attempt. The failure report alone does not establish that prose variation caused that earlier error. Both attempts used the real provider and incurred usage; monetary cost was not measured.

After extracting the same renderer into a testable helper, 34 deterministic tests passed in the locked environment. New negative controls reject missing observations, repeated voice user turns, incomplete lifecycle, empty/silent/oversized/partial PCM and invalid codes. They validate diagnostic semantics, not provider quality. Ruff 0.14.0 passed on both new files; the repository checker passed with 46 Markdown files and 16 ADRs, and `git diff --check` passed.

## Reproduce

```bash
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env \
  python scripts/check_voice.py --allow-live --output artifacts/compatibility/voice.json
python3 -m unittest discover -s tests/compatibility -v
```

The pinned provider and workflow contracts were inspected in the installed package. Official architecture and example: [Voice agents — chained workflow](https://developers.openai.com/api/docs/guides/voice-agents#build-a-chained-voice-workflow).

Remaining acceptance: real browser microphone/playback, codec conversion, human listening, noisy speech/silence, cancellation/disconnect behavior, customer identity and authorization, Engine-backed continuity, and repeated evaluation. No application, deployment, durable session support, or full Phase 0 acceptance is claimed. Changes are locally authored and uncommitted.


## Hosted Engine voice and chat proof: 2026-10-29

[check_voice_engine.py](../../scripts/check_voice_engine.py) replaces the diagnostic's ephemeral SDK history path with the existing hosted recall fixture. OpenAI VoicePipeline handles STT/TTS; its custom workflow invokes the Engine CLI, checks the exact synthetic pending action and scope, approves that fixture, validates the completed result, and only then releases the fixed speech text. The OpenAI Runner executes inside Engine. No local text-model Runner or second memory writer is introduced.

The [live report](../../compatibility/voice-engine-evidence.json) passed two distinct executions in one session: generated speech and following chat both recalled the previously stored marker, which is absent from their requests. Input/output audio lasted 4.65/7.85 seconds (not latency measurements). A metadata-only Engine-store audit found six turns, sequences 1–6 and six distinct idempotency hashes. This proves channel continuity for an existing durable fact, not retention of a newly spoken fact or full chronological history.

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/check_voice_engine.py --allow-live --output artifacts/compatibility/voice-engine.json
```

## Synthetic browser codec and playback proof

[serve_voice_engine_probe.py](../../scripts/serve_voice_engine_probe.py) serves a one-shot localhost [test page](../../scripts/voice_engine_probe.html), with exact Host/Origin checks, a per-process request nonce, bounded request/audio sizes and no provider credentials in the page. A real foreign-origin request returned 403. It is a synthetic diagnostic, not an authenticated customer gateway. It binds only 127.0.0.1 and accepts one ordered fixture/voice/chat/playback sequence per process.

In Chrome, generated speech passed through AudioContext → MediaStreamDestination → MediaRecorder (`audio/webm;codecs=opus`, 75,644 encoded bytes), browser decoding and mono 24 kHz PCM conversion. That PCM passed the real VoicePipeline/Engine review flow; following chat used the same Engine user/session. Browser playback reached `ended`. [Successful evidence](../../compatibility/browser-voice-engine-evidence.json) records two completed executions, the native voice lifecycle and browser-reported codec/playback metadata. The store separately contained six turns with distinct sequences/hashes. Audio was held in memory and not committed or logged. No microphone was opened, and no human-listening result is claimed.

The [first browser attempt](../../compatibility/browser-voice-engine-failed-evidence.json) failed with RuntimeError during `/voice`; the diagnostic had recorded no execution ID. An independent storage audit nevertheless found two turns (user/assistant), so that failure **did have remote effects**. It must not be described as a pre-dispatch failure or zero-cost attempt. Its precise cause was not captured by the initial diagnostic. A fresh one-shot process with safe stack-frame reporting then passed. No provider/Engine configuration or deployment changed between attempts. Automatic retries are not added.

```sh
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env python scripts/serve_voice_engine_probe.py --allow-live --output artifacts/compatibility/browser-voice-engine.json
```

Open `http://127.0.0.1:8768`, run the synthetic test, then play the approved response. Stop the diagnostic server with Ctrl-C afterward. A successful run makes three direct audio-provider requests plus two hosted model/read-tool executions and native approvals; failures may still incur usage or writes. Monetary cost was not measured. The CLI calls have bounded timeouts and no retry; cancelling a client does not cancel remote work already accepted.

Seven new local tests reject changed action/result/scope/requester, check approval-before-speech, explicit live gating, origin/nonce enforcement and the WAV contract. All 66 compatibility tests passed; JavaScript syntax checking passed. [Cancellation contract tests](COMP-003-FAULTS.md) cover local cancellation separately. Remaining browser acceptance is real microphone/human listening, noisy/silent speech, disconnection/cancellation across remote boundaries and independent customer identity. Engine requester authorization and lossless chronological restoration remain separately blocked; this test does not bypass those production gates.
