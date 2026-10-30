"""Speech stage boundaries with signature-checked SDK doubles; no provider traffic."""
import asyncio
import base64
import io
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from agents.voice.model import STTModel, TTSModel

from telecom_app.voice import VoiceService


def providers(monkeypatch, stt=None, tts=None):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=client)
    monkeypatch.setattr("openai.AsyncOpenAI", factory)
    monkeypatch.setattr(
        "agents.voice.models.openai_model_provider.OpenAIVoiceModelProvider",
        lambda **kwargs: SimpleNamespace(get_stt_model=lambda name: stt,
                                        get_tts_model=lambda name: tts),
    )
    return factory


def test_transcription_uses_bounded_pcm_and_disables_trace_audio(monkeypatch):
    stt = create_autospec(STTModel, instance=True)
    stt.transcribe.return_value = " Read demo-1 "
    factory = providers(monkeypatch, stt=stt)
    pcm = b"\x00\x10" * 6000
    output = asyncio.run(VoiceService().transcribe(base64.b64encode(pcm).decode()))
    assert output == "Read demo-1"
    factory.assert_called_once_with(max_retries=0, timeout=45)
    args = stt.transcribe.call_args.args
    assert args[0].buffer.tobytes() == pcm
    assert args[1].language == "en" and args[2:] == (False, False)


def test_tts_returns_mono_pcm_wav_without_changing_verified_text(monkeypatch):
    tts = create_autospec(TTSModel, instance=True)
    async def chunks(*args):
        yield b"\x00\x10" * 6000
    tts.run.side_effect = chunks
    providers(monkeypatch, tts=tts)
    text = "Your synthetic invoice total is USD 79.90, due on 2026-12-01."
    result = asyncio.run(VoiceService().speak(text))
    assert tts.run.call_args.args[0] == text
    with wave.open(io.BytesIO(result)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
        assert wav.getnframes() == 6000


def test_provider_failure_has_no_retry(monkeypatch):
    stt = create_autospec(STTModel, instance=True)
    stt.transcribe.side_effect = TimeoutError("synthetic")
    providers(monkeypatch, stt=stt)
    with pytest.raises(TimeoutError):
        asyncio.run(VoiceService().transcribe(base64.b64encode(b"\x00\x10" * 6000).decode()))
    stt.transcribe.assert_awaited_once()
