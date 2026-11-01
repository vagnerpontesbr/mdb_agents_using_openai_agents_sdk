"""Bounded speech stages using SDK providers; no recordings or transcript storage."""

import base64
import binascii
import io
import wave
from typing import Any

from .contracts import Contract
from .profile import Locale
from .turn_locale import validated_locale

RATE = 24000
MAX_PCM = RATE * 2 * 15


class AudioInput(Contract):
    pcm_base64: str
    locale: Locale = "en-US"


def pcm_bytes(encoded: str) -> bytes:
    if len(encoded) > (MAX_PCM * 4 // 3 + 4):
        raise ValueError("Audio exceeds 15 seconds")
    try:
        pcm = base64.b64decode(encoded, validate=True)
    except ValueError, binascii.Error:
        raise ValueError("Invalid PCM") from None
    if not pcm or len(pcm) > MAX_PCM or len(pcm) % 2:
        raise ValueError("Invalid PCM")
    import numpy as np

    samples = np.frombuffer(pcm, dtype="<i2")
    if len(samples) < RATE // 4 or float(np.max(np.abs(samples.astype(float)))) < 128:
        raise ValueError("No audible speech detected")
    return pcm


class VoiceService:
    async def transcribe(self, encoded: str, locale: Locale = "en-US") -> str:
        import numpy as np
        from agents.voice import AudioInput as SDKAudio
        from agents.voice.model import STTModelSettings
        from agents.voice.models.openai_model_provider import OpenAIVoiceModelProvider
        from openai import AsyncOpenAI

        language = {"en-US": "en", "pt-BR": "pt", "es-ES": "es"}[validated_locale(locale)]
        pcm = pcm_bytes(encoded)
        async with AsyncOpenAI(max_retries=0, timeout=45) as client:
            model = OpenAIVoiceModelProvider(openai_client=client).get_stt_model(
                "gpt-4o-mini-transcribe"
            )
            result: Any = await model.transcribe(
                SDKAudio(buffer=np.frombuffer(pcm, dtype="<i2")),
                STTModelSettings(language=language),
                False,
                False,
            )
        if not isinstance(result, str) or not 1 <= len(result.strip()) <= 4000:
            raise ValueError("No usable transcript")
        return result.strip()

    async def speak(self, text: str, locale: Locale = "en-US") -> bytes:
        from agents.voice.model import TTSModelSettings
        from agents.voice.models.openai_model_provider import OpenAIVoiceModelProvider
        from openai import AsyncOpenAI

        language = {"en-US": "American English", "pt-BR": "Brazilian Portuguese",
                    "es-ES": "Spanish (Spain)"}[validated_locale(locale)]
        if not text or len(text) > 8000:
            raise ValueError("Invalid speech text")
        pcm = bytearray()
        async with AsyncOpenAI(max_retries=0, timeout=45) as client:
            model = OpenAIVoiceModelProvider(openai_client=client).get_tts_model("gpt-4o-mini-tts")
            settings = TTSModelSettings(
                voice="alloy", instructions=f"Read the supplied text in {language}. "
                "Use only this language throughout; never switch languages. "
                "Do not translate, add or omit words. Preserve dates and negations. "
                "Read monetary decimals as currency units and cents, never as thousands."
            )
            async for chunk in model.run(text, settings):
                pcm.extend(chunk)
                if len(pcm) > RATE * 2 * 120:
                    raise ValueError("Speech output exceeds bound")
        if not pcm or len(pcm) % 2:
            raise ValueError("Invalid speech output")
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(pcm)
        return output.getvalue()
