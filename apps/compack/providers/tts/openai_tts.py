from __future__ import annotations

import asyncio
from typing import Optional

import openai

from apps.compack.modules.tts import TTSProvider


class OpenAITTSTTS(TTSProvider):
    """OpenAI TTS API 実装."""

    def __init__(self, api_key: str, voice: str = "alloy", model: str = "gpt-4o-mini-tts", speed: float = 1.0):
        self.client = openai.OpenAI(api_key=api_key)
        self.voice = voice
        self.model = model
        self.speed = speed

    async def synthesize(self, text: str) -> bytes:
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        response = self.client.audio.speech.create(model=self.model, voice=self.voice, input=text, speed=self.speed)
        if hasattr(response, "read"):
            return response.read()
        audio: Optional[bytes] = getattr(response, "audio", None)
        if audio:
            return audio
        return bytes(response)
