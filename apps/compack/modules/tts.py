from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from apps.compack.core import StructuredLogger


class TTSError(Exception):
    """TTS related errors."""


class TTSProvider(ABC):
    """TTSプロバイダ抽象基底クラス."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesize audio bytes from text."""
        raise NotImplementedError


class TTSModule:
    """音声合成と再生のファサード."""

    def __init__(self, provider: TTSProvider, logger: StructuredLogger):
        self.provider = provider
        self.logger = logger

    async def synthesize(self, text: str) -> bytes:
        if not text:
            raise TTSError("合成するテキストが空です。")
        try:
            audio = await self.provider.synthesize(text)
            if not audio:
                raise TTSError("音声合成結果が空でした。")
            self.logger.info("音声合成成功", bytes=len(audio))
            return audio
        except Exception as exc:
            self.logger.error("音声合成に失敗しました", error=exc)
            raise

    def play_audio(self, audio_data: bytes) -> None:
        try:
            import pygame
        except ImportError as exc:
            self.logger.error("再生デバイスが見つかりません", error=exc)
            raise TTSError("音声出力デバイスが見つかりません。") from exc

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(buffer=audio_data)
            channel = sound.play()
            while channel.get_busy():
                pygame.time.delay(10)
            self.logger.info("音声再生完了")
        except Exception as exc:
            self.logger.error("音声再生に失敗しました", error=exc)
            raise TTSError("音声再生に失敗しました。") from exc
