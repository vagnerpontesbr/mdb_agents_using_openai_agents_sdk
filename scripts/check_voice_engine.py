"""Opt-in synthetic speech -> hosted Engine -> speech and chat probe.

The existing CLI caller approves only the exact synthetic fixture. This is not
end-user authentication or a production voice gateway. Audio stays in memory.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import uuid

if __package__:
    from .check_voice import RATE, MAX_BYTES, validate_pcm
else:
    from check_voice import RATE, MAX_BYTES, validate_pcm

PROJECT = "67b385a7976edf15ecc62e06"
ORG = "663e3089acf80f05b63effcf"
WORKSPACE = "ws-6ae20f53f3b040aa65fa961a"
USER = "phase0-user-98751e7966484cf3a7703be3086aa820"
MARKER = "SYNTHETIC-PROBE-98751e7966484cf3a7703be3086aa820"
PROMPT = "Read invoice demo one and recall my synthetic verification marker."
CHAT = "Read invoice demo-1 again and recall my synthetic verification marker."
SPOKEN = "Your synthetic invoice is 79 dollars and 90 cents. Your stored verification marker was recalled."
EXPECTED = {"invoice_id": "demo-1", "amount_minor": 7990, "currency": "USD",
            "synthetic": True, "model_reported_marker": MARKER}


def validate_scope(response, session):
    if not isinstance(response, dict) or response.get("success") is not True:
        raise ValueError("Engine operation did not succeed")
    expected = {"project_id": PROJECT, "org_id": ORG, "workspace_id": WORKSPACE,
                "session_id": session}
    if any(response.get(k) != v for k, v in expected.items()):
        raise ValueError("Engine response scope mismatch")
    execution = response.get("execution_id")
    if not isinstance(execution, str) or not execution:
        raise ValueError("Missing execution identity")
    return execution


def validate_pending(response, session):
    execution = validate_scope(response, session)
    if response.get("suspended") is not True:
        raise ValueError("Native review was not reached")
    interrupts = response.get("suspend_context", {}).get("interrupts")
    if not isinstance(interrupts, list) or len(interrupts) != 1:
        raise ValueError("Expected one pending review")
    interrupt = interrupts[0]
    review = interrupt.get("value", {})
    action = {"arguments": EXPECTED, "tool_call_id": "release-demo-1",
              "tool_name": "release_synthetic_recall"}
    if (review.get("action") != action or review.get("requesting_user_id") != USER
            or review.get("contract") != "openai-engine-review-v1"
            or review.get("allowed_decisions") != ["approve", "reject"]
            or not isinstance(interrupt.get("id"), str) or not interrupt["id"]):
        raise ValueError("Unexpected action; no approval sent")
    return execution, interrupt["id"]


def validate_completed(response, session, execution):
    if validate_scope(response, session) != execution or response.get("suspended"):
        raise ValueError("Resume did not complete the original execution")
    if json.loads(response.get("response", "null")) != EXPECTED:
        raise ValueError("Unexpected result; no speech released")
    return SPOKEN


async def invoke_cli(session, *, message=None, review=None):
    args = ["agentengine", "invoke"]
    if review is not None:
        args += ["--resume", json.dumps({review: {"decision": "approve"}})]
    else:
        args += [message]
    args += ["--session", session, "--user-id", USER, "--json", "--timeout", "90s",
             "--base-url", "https://agentengine.mongodb.com", "--org-id", ORG,
             "--project-id", PROJECT, "--workspace-id", WORKSPACE, "--no-log"]
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=100)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    if process.returncode != 0 or len(stdout) > 1_000_000:
        raise RuntimeError("CLI failed; raw output suppressed")
    return json.loads(stdout)


async def engine_turn(session, message, calls):
    pending = await invoke_cli(session, message=message)
    execution, review = validate_pending(pending, session)
    # Persist only metadata in the diagnostic report, never audio/transcription.
    calls.append({"execution_id": execution, "review_id": review, "completed": False})
    completed = await invoke_cli(session, review=review)
    result = validate_completed(completed, session, execution)
    calls[-1]["completed"] = True
    return result


async def fixture_audio(client):
    from agents.voice.model import TTSModelSettings
    from agents.voice.models.openai_model_provider import OpenAIVoiceModelProvider
    tts = OpenAIVoiceModelProvider(openai_client=client).get_tts_model("gpt-4o-mini-tts")
    fixture = bytearray()
    async for chunk in tts.run(PROMPT, TTSModelSettings(voice="alloy")):
        fixture.extend(chunk)
        if len(fixture) > MAX_BYTES:
            raise ValueError("Fixture exceeds audio limit")
    validate_pcm(fixture)
    return bytes(fixture)


async def voice_turn(fixture, session, calls, client):
    import numpy as np
    from agents.voice import AudioInput, VoicePipeline, VoicePipelineConfig, VoiceWorkflowBase
    from agents.voice.model import STTModelSettings, TTSModelSettings
    from agents.voice.models.openai_model_provider import OpenAIVoiceModelProvider
    validate_pcm(fixture)
    provider = OpenAIVoiceModelProvider(openai_client=client)
    stt = provider.get_stt_model("gpt-4o-mini-transcribe")
    tts = provider.get_tts_model("gpt-4o-mini-tts")

    class Workflow(VoiceWorkflowBase):
        async def run(self, transcription):
            if (len(transcription) > 300 or MARKER in transcription
                    or not all(word in transcription.lower()
                               for word in ("invoice", "synthetic", "marker"))):
                raise ValueError("Unexpected synthetic transcription")
            yield await engine_turn(session, transcription, calls)

    pipeline = VoicePipeline(workflow=Workflow(), stt_model=stt, tts_model=tts,
        config=VoicePipelineConfig(model_provider=provider, tracing_disabled=True,
            trace_include_sensitive_data=False, trace_include_sensitive_audio_data=False,
            stt_settings=STTModelSettings(language="en"),
            tts_settings=TTSModelSettings(voice="alloy")))
    result = await pipeline.run(AudioInput(buffer=np.frombuffer(fixture, dtype="<i2")))
    output, lifecycle = bytearray(), []
    async for event in result.stream():
        if event.type == "voice_stream_event_error":
            raise event.error
        if event.type == "voice_stream_event_lifecycle":
            lifecycle.append(event.event)
        if event.type == "voice_stream_event_audio" and event.data is not None:
            output.extend(event.data.astype("<i2").tobytes())
            if len(output) > MAX_BYTES:
                raise ValueError("Output exceeds audio limit")
    validate_pcm(output)
    if lifecycle != ["turn_started", "turn_ended", "session_ended"]:
        raise ValueError("Incomplete voice lifecycle")
    return bytes(output), lifecycle


async def live():
    from openai import AsyncOpenAI
    session = "phase0-voice-engine-" + uuid.uuid4().hex[:12]
    report = {"session_id": session, "user_id": USER, "calls": [], "status": "fail"}
    stage = "fixture_tts"
    try:
        async with AsyncOpenAI(timeout=30, max_retries=0) as client:
            fixture = await fixture_audio(client)
            stage = "speech_engine_speech"
            output, lifecycle = await voice_turn(fixture, session, report["calls"], client)
            stage = "chat_continuation"
            chat = await engine_turn(session, CHAT, report["calls"])
            if chat != SPOKEN or len({r["execution_id"] for r in report["calls"]}) != 2:
                raise ValueError("Expected two distinct completed turns")
            report.update(status="pass", lifecycle=lifecycle,
                          input_audio_seconds=len(fixture) / (RATE * 2),
                          output_audio_seconds=len(output) / (RATE * 2),
                          stored_marker_recalled_in_both_channels=True,
                          ephemeral_sdk_history_used=False)
    except Exception as error:
        report.update(failed_stage=stage, error_class=type(error).__name__)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    if not args.allow_live or not os.environ.get("OPENAI_API_KEY"):
        report = {"status": "blocked", "reason": "Requires --allow-live and OPENAI_API_KEY"}
    else:
        report = asyncio.run(live())
    report.update(recorded_at=datetime.now(timezone.utc).isoformat(), phase0_complete=False,
        scope="Synthetic audio plus hosted memory recall across voice/chat; no browser proof",
        limitations=["One CLI identity automatically approves the exact synthetic fixture only.",
                     "Both channels recall a previously stored marker; no new-fact retention proof.",
                     "No microphone, listening, browser codec or independent approver auth test.",
                     "Stopping the CLI does not cancel already accepted Engine/provider work."])
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n")
    print(encoded)
    return {"pass": 0, "fail": 1, "blocked": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
