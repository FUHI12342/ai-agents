from __future__ import annotations

import asyncio
import io
from typing import Optional

import numpy as np
import openai

from apps.compack.modules.stt import STTProvider
from apps.compack.utils.audio import to_wav_bytes


class OpenAIWhisperSTT(STTProvider):
    """OpenAI Whisper API 実装."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        audio_bytes = to_wav_bytes(audio_data, sample_rate)
        return await asyncio.to_thread(self._transcribe_sync, audio_bytes)

    def _transcribe_sync(self, audio_bytes: bytes) -> str:
        with io.BytesIO(audio_bytes) as buffer:
            buffer.name = "audio.wav"
            response = self.client.audio.transcriptions.create(model=self.model, file=buffer)
        text: Optional[str] = getattr(response, "text", None) if response is not None else None
        if text is None and isinstance(response, dict):
            text = response.get("text")
        return text or ""
