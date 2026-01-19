from __future__ import annotations

import asyncio
from typing import Optional

import numpy as np

from apps.compack.modules.stt import STTProvider
from apps.compack.utils.audio import to_wav_bytes


class LocalWhisperSTT(STTProvider):
    """ローカル Whisper モデル実装."""

    def __init__(self, model_name: str = "base"):
        try:
            import whisper  # type: ignore
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError("whisper ライブラリが見つかりません。") from exc
        self.whisper = whisper
        self.model = whisper.load_model(model_name)
        self.model_name = model_name

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        audio_bytes = to_wav_bytes(audio_data, sample_rate)
        return await asyncio.to_thread(self._run_model, audio_bytes)

    def _run_model(self, audio_bytes: bytes) -> str:
        import io

        with io.BytesIO(audio_bytes) as buffer:
            result: Optional[dict] = self.model.transcribe(buffer, fp16=False)
        if not result:
            return ""
        text = result.get("text") if isinstance(result, dict) else None
        return text or ""
