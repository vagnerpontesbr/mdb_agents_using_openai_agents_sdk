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


@pytest.mark.parametrize("locale,hint", [("en-US", "en"), ("pt-BR", "pt"), ("es-ES", "es")])
def test_transcription_uses_bounded_pcm_and_disables_trace_audio(monkeypatch, locale, hint):
    stt = create_autospec(STTModel, instance=True)
    stt.transcribe.return_value = " Read demo-1 "
    factory = providers(monkeypatch, stt=stt)
    pcm = b"\x00\x10" * 6000
    output = asyncio.run(VoiceService().transcribe(base64.b64encode(pcm).decode(), locale))
    assert output == "Read demo-1"
    factory.assert_called_once_with(max_retries=0, timeout=45)
    args = stt.transcribe.call_args.args
    assert args[0].buffer.tobytes() == pcm
    assert args[1].language == hint and args[2:] == (False, False)


@pytest.mark.parametrize("locale,text,language", [
    ("en-US", "Do not change the plan. USD 79.90, due on 2026-12-01.", "American English"),
    ("pt-BR", "Não altere o plano. USD 79,90, vencimento em 01/12/2026.", "Brazilian Portuguese"),
    ("es-ES", "No cambies el plan. USD 79,90, vence el 01/12/2026.", "Spanish (Spain)"),
])
def test_tts_returns_mono_pcm_wav_without_changing_verified_text(
    monkeypatch, locale, text, language
):
    tts = create_autospec(TTSModel, instance=True)
    async def chunks(*args):
        yield b"\x00\x10" * 6000
    tts.run.side_effect = chunks
    providers(monkeypatch, tts=tts)
    result = asyncio.run(VoiceService().speak(text, locale))
    assert tts.run.call_args.args[0] == text
    assert language in tts.run.call_args.args[1].instructions
    assert tts.run.call_args.args[1].voice == "alloy"
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


@pytest.mark.parametrize("locale", ["en-US", "pt-BR", "es-ES"])
@pytest.mark.parametrize("encoded", ["!", "", "AA==", "AAAA", "AAA=" * 250000])
def test_invalid_audio_rejected_before_client_creation(monkeypatch, locale, encoded):
    factory = providers(monkeypatch)
    with pytest.raises(ValueError):
        asyncio.run(VoiceService().transcribe(encoded, locale))
    factory.assert_not_called()


def test_unknown_locale_rejected_before_provider(monkeypatch):
    factory = providers(monkeypatch)
    with pytest.raises(ValueError):
        asyncio.run(VoiceService().speak("synthetic", "fr-FR"))
    with pytest.raises(ValueError):
        asyncio.run(VoiceService().transcribe("AAAA", "fr-FR"))
    factory.assert_not_called()


def test_live_evaluator_is_bounded_and_refuses_existing_evidence(tmp_path, monkeypatch):
    from scripts import check_multilingual_voice as gate

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x10" * 6000)
    speech = SimpleNamespace(speak=AsyncMock(return_value=output.getvalue()),
                             transcribe=AsyncMock(return_value="Synthetic transcript"))
    monkeypatch.setattr(gate, "VoiceService", lambda: speech)
    target = tmp_path / "evidence"
    asyncio.run(gate.evaluate(target))
    assert speech.speak.await_count == speech.transcribe.await_count == 3
    with pytest.raises(FileExistsError):
        asyncio.run(gate.evaluate(target))
    assert speech.speak.await_count == 3


def test_live_evaluator_stops_after_uncertain_provider_failure(tmp_path, monkeypatch):
    import json

    from scripts import check_multilingual_voice as gate

    speech = SimpleNamespace(speak=AsyncMock(side_effect=TimeoutError("private detail")),
                             transcribe=AsyncMock())
    monkeypatch.setattr(gate, "VoiceService", lambda: speech)
    target = tmp_path / "evidence"
    with pytest.raises(SystemExit):
        asyncio.run(gate.evaluate(target))
    speech.speak.assert_awaited_once()
    speech.transcribe.assert_not_called()
    text = (target / "evidence.json").read_text()
    assert "private detail" not in text
    assert json.loads(text)["provider_requests_started"] == 1


@pytest.mark.parametrize("locale,text,language", [
    ("en-US", "Do not change fiber-500. USD 79.90.", "American English"),
    ("pt-BR", "Não altere o fiber-500. USD 79,90.", "Brazilian Portuguese"),
    ("es-ES", "No cambies fiber-500. USD 79,90.", "Spanish (Spain)"),
])
def test_real_sdk_http_payload_keeps_input_and_language(monkeypatch, locale, text, language):
    """Exercise both pinned SDKs through HTTP serialization, without provider traffic."""
    import json

    import httpx
    from openai import AsyncOpenAI

    requests = []

    def respond(request):
        assert request.url.path == "/v1/audio/speech"
        requests.append(json.loads(request.content))
        return httpx.Response(200, content=b"\x00\x10" * 6000,
                              headers={"content-type": "application/octet-stream"})

    def client(**kwargs):
        return AsyncOpenAI(api_key="synthetic-test-only", base_url="https://speech.example.test/v1",
                           http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
                           **kwargs)

    monkeypatch.setattr("openai.AsyncOpenAI", client)
    result = asyncio.run(VoiceService().speak(text, locale))
    assert result.startswith(b"RIFF")
    assert len(requests) == 1
    assert requests[0]["input"] == text
    assert requests[0]["model"] == "gpt-4o-mini-tts"
    assert requests[0]["voice"] == "alloy"
    assert requests[0]["response_format"] == "pcm"
    assert requests[0]["instructions"] == (
        f"Read the supplied text in {language}. "
        "Use only this language throughout; never switch languages. "
        "Do not translate, add or omit words. Preserve dates and negations. "
        "Read monetary decimals as currency units and cents, never as thousands."
    )
