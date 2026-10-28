"""Opt-in synthetic voice diagnostic. No microphone, playback or durable memory."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys

RATE = 24000
MAX_BYTES = RATE * 2 * 20
UTTERANCE = "My synthetic support code is cobalt. Please repeat my support code."
FOLLOWUP = "What support code did I give you in my previous message?"
EXPECTED = "Your support code is cobalt."


def render_code(code: str | None) -> str:
    if code is None:
        return "No support code supplied."
    normalized = code.strip().lower()
    if not re.fullmatch(r"[a-z]{1,24}", normalized):
        raise ValueError("Invalid synthetic support code")
    return f"Your support code is {normalized}."


def validate_pcm(data: bytes) -> None:
    if not data or len(data) % 2 or len(data) > MAX_BYTES:
        raise ValueError("PCM must contain complete 16-bit samples within twenty seconds")
    if not any(data):
        raise ValueError("Silent PCM does not establish speech output")


def evaluate(transcript: str, voice_text: str, spoken_text: str, chat_text: str,
             user_turns: int, audio_bytes: int, events: list[str]) -> dict:
    checks = {
        "input_marker_transcribed": bool(re.search(r"\bcobalt\b", transcript.lower())),
        "voice_response_exact": voice_text == EXPECTED,
        "output_marker_transcribed": bool(re.search(r"\bcobalt\b", spoken_text.lower())),
        "chat_continuity_exact": chat_text == EXPECTED,
        "voice_user_turn_recorded_once": user_turns == 1,
        "output_audio_bounded": 0 < audio_bytes <= MAX_BYTES,
        "turn_lifecycle_complete": events == ["turn_started", "turn_ended", "session_ended"],
    }
    return {"status": "pass" if all(checks.values()) else "fail", "checks": checks}


async def live() -> dict:
    import numpy as np
    from openai import AsyncOpenAI
    from pydantic import BaseModel
    from agents import Agent, ModelSettings, OpenAIResponsesModel, RunConfig, Runner
    from agents.voice import AudioInput, VoicePipeline, VoicePipelineConfig, VoiceWorkflowBase
    from agents.voice.model import STTModelSettings, TTSModelSettings
    from agents.voice.models.openai_model_provider import OpenAIVoiceModelProvider

    stage = "fixture_tts"
    try:
        async with AsyncOpenAI(timeout=30, max_retries=0) as client:
            provider = OpenAIVoiceModelProvider(openai_client=client)
            stt = provider.get_stt_model("gpt-4o-mini-transcribe")
            tts = provider.get_tts_model("gpt-4o-mini-tts")
            settings = TTSModelSettings(voice="alloy")
            fixture = bytearray()
            async for chunk in tts.run(UTTERANCE, settings):
                fixture.extend(chunk)
                if len(fixture) > MAX_BYTES:
                    raise ValueError("Fixture audio exceeds diagnostic limit")
            validate_pcm(fixture)
            class SupportCode(BaseModel):
                code: str | None

            def render(value):
                if not isinstance(value, SupportCode):
                    raise ValueError("Missing structured support code")
                return render_code(value.code)

            agent = Agent(
                name="Phase0VoiceProbe",
                instructions=("Extract the synthetic support code from the conversation. "
                              "Return null if no code was supplied. Do not invent a code."),
                output_type=SupportCode,
                model=OpenAIResponsesModel(model=os.environ["OPENAI_MODEL"], openai_client=client),
                model_settings=ModelSettings(max_tokens=256),
            )

            class Workflow(VoiceWorkflowBase):
                def __init__(self):
                    self.history = []
                    self.transcript = ""
                    self.answer = ""

                async def run(self, transcription):
                    self.transcript = transcription
                    result = await Runner.run(
                        agent, transcription, max_turns=1,
                        run_config=RunConfig(tracing_disabled=True),
                    )
                    self.history = result.to_input_list()
                    self.answer = render(result.final_output)
                    # Validate the whole response before releasing speech.
                    if self.answer != EXPECTED:
                        raise ValueError("Voice response did not match expected synthetic contract")
                    yield self.answer

            workflow = Workflow()
            stage = "voice_pipeline"
            pipeline = VoicePipeline(workflow=workflow, stt_model=stt, tts_model=tts,
                                     config=VoicePipelineConfig(
                                         model_provider=provider, tracing_disabled=True,
                                         trace_include_sensitive_data=False,
                                         trace_include_sensitive_audio_data=False,
                                         stt_settings=STTModelSettings(language="en"),
                                         tts_settings=settings))
            result = await pipeline.run(AudioInput(buffer=np.frombuffer(fixture, dtype="<i2")))
            output = bytearray()
            events = []
            async for event in result.stream():
                if event.type == "voice_stream_event_error":
                    raise event.error
                if event.type == "voice_stream_event_lifecycle":
                    events.append(event.event)
                if event.type == "voice_stream_event_audio" and event.data is not None:
                    output.extend(event.data.astype("<i2").tobytes())
                    if len(output) > MAX_BYTES:
                        raise ValueError("Output audio exceeds diagnostic limit")
            validate_pcm(output)
            stage = "output_transcription"
            spoken = await stt.transcribe(AudioInput(buffer=np.frombuffer(output, dtype="<i2")),
                                          STTModelSettings(language="en"), False, False)
            stage = "chat_continuation"
            turns = sum(item.get("role") == "user" for item in workflow.history)
            chat = await Runner.run(
                agent, workflow.history + [{"role": "user", "content": FOLLOWUP}],
                max_turns=1, run_config=RunConfig(tracing_disabled=True),
            )
            evidence = evaluate(workflow.transcript, workflow.answer, spoken,
                                render(chat.final_output), turns, len(output), events)
            return {**evidence, "output_audio_seconds": len(output) / (RATE * 2),
                    "input_audio_seconds": len(fixture) / (RATE * 2),
                    "lifecycle_events": events, "agent_model": os.environ["OPENAI_MODEL"],
                    "stt_model": stt.model_name, "tts_model": tts.model_name,
                    "history_backend": "ephemeral SDK input items; not Engine memory"}
    except Exception as exc:
        return {"status": "fail", "failed_stage": stage, "error_class": type(exc).__name__,
                "detail": "Sensitive exception text suppressed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    if not args.allow_live:
        report = {"status": "blocked", "detail": "Requires --allow-live; up to six provider requests"}
    elif not all(os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_MODEL")):
        report = {"status": "blocked", "detail": "OPENAI_API_KEY and OPENAI_MODEL are required"}
    elif args.worker:
        report = asyncio.run(live())
    else:
        try:
            child = subprocess.run([sys.executable, __file__, "--allow-live", "--worker"],
                                   capture_output=True, text=True, timeout=150)
            report = json.loads(child.stdout) if child.returncode in (0, 1, 2) else {
                "status": "fail", "detail": "Worker failed; raw output suppressed"}
        except subprocess.TimeoutExpired:
            report = {"status": "fail", "detail": "Worker exceeded 150-second deadline"}
        except ValueError:
            report = {"status": "fail", "detail": "Worker returned invalid evidence"}
    report.update(recorded_at=datetime.now(timezone.utc).isoformat(), phase0_complete=False,
                  scope="synthetic voice and in-process chat continuity; no browser or Engine proof")
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n")
    print(encoded)
    return {"pass": 0, "fail": 1, "blocked": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
