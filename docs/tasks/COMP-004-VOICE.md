# COMP-004: Synthetic voice round trip and chat continuation

- Status: Bounded provider proof passed; browser and Engine session integration pending
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
