from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np

from apps.compack.core import StructuredLogger


class STTError(Exception):
    """STT related errors."""


class STTProvider(ABC):
    """STTプロバイダ抽象基底クラス."""

    @abstractmethod
    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Convert audio data to text."""
        raise NotImplementedError


class STTModule:
    """音声録音とテキスト化のファサード."""

    def __init__(
        self,
        provider: STTProvider,
        logger: StructuredLogger,
        sample_rate: int = 16000,
        channels: int = 1,
    ):
        self.provider = provider
        self.logger = logger
        self.sample_rate = sample_rate
        self.channels = channels

    def record_audio(self, duration: float = 5.0) -> Tuple[np.ndarray, int]:
        """Record audio for the given duration."""
        try:
            import sounddevice as sd
        except ImportError as exc:
            self.logger.error("録音デバイスの初期化に失敗しました", error=exc)
            raise STTError("録音デバイスが見つかりません。") from exc

        try:
            frames = int(duration * self.sample_rate)
            recording = sd.rec(frames, samplerate=self.sample_rate, channels=self.channels, dtype="float32")
            sd.wait()
            self.logger.info("録音完了", frames=frames, sample_rate=self.sample_rate, channels=self.channels)
            return np.squeeze(recording), self.sample_rate
        except Exception as exc:
            self.logger.error("録音に失敗しました", error=exc)
            raise STTError("録音に失敗しました。") from exc

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Transcribe recorded audio into text using the configured provider."""
        try:
            text = await self.provider.transcribe(audio_data, sample_rate)
            if not text:
                raise STTError("音声認識結果が空でした。")
            self.logger.info("音声認識成功", provider=self.provider.__class__.__name__, length=len(text))
            return text
        except Exception as exc:
            self.logger.error("音声認識に失敗しました", error=exc)
            raise

