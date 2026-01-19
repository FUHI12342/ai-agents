from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile

from apps.compack.modules.tts import TTSProvider


class Pyttsx3TTS(TTSProvider):
    """pyttsx3 ローカル TTS 実装."""

    def __init__(self, rate: int = 150, volume: float = 1.0):
        try:
            import pyttsx3  # type: ignore
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError("pyttsx3 がインストールされていません。") from exc

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

    async def synthesize(self, text: str) -> bytes:
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        with NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            self.engine.save_to_file(text, tmp.name)
            self.engine.runAndWait()
            tmp.seek(0)
            return tmp.read()
