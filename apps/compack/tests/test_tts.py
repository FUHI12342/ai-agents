import sys
import types

import pytest
from hypothesis import given, strategies as st

from apps.compack.core import StructuredLogger
from apps.compack.modules import TTSModule, TTSProvider


class FakeTTSProvider(TTSProvider):
    async def synthesize(self, text: str) -> bytes:  # pragma: no cover - simple stub
        return text.encode("utf-8") or b"x"


class DummyChannel:
    def __init__(self):
        self.calls = 0

    def get_busy(self) -> bool:
        self.calls += 1
        return self.calls == 1


class DummySound:
    def __init__(self, buffer: bytes):
        self.buffer = buffer

    def play(self) -> DummyChannel:
        return DummyChannel()


class DummyMixer:
    def __init__(self):
        self.initialized = False

    def get_init(self):
        return self.initialized

    def init(self):
        self.initialized = True

    def Sound(self, buffer: bytes) -> DummySound:  # noqa: N802 - following pygame API
        return DummySound(buffer)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tts_synthesize_returns_bytes() -> None:
    module = TTSModule(FakeTTSProvider(), StructuredLogger(log_file=None))
    audio = await module.synthesize("hello")
    assert isinstance(audio, (bytes, bytearray))
    assert audio


@pytest.mark.unit
def test_play_audio_uses_pygame(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_pygame = types.ModuleType("pygame")
    dummy_pygame.mixer = DummyMixer()
    dummy_pygame.time = type("time", (), {"delay": staticmethod(lambda ms: None)})
    monkeypatch.setitem(sys.modules, "pygame", dummy_pygame)

    module = TTSModule(FakeTTSProvider(), StructuredLogger(log_file=None))
    module.play_audio(b"1234")  # should not raise


@pytest.mark.property
@pytest.mark.asyncio
@given(text=st.text(min_size=1, max_size=50))
async def test_tts_audio_non_empty(text: str) -> None:
    """
    Feature: voice-ai-agent-compack, Property 5: TTSオーディオ生成の非空性.
    """
    module = TTSModule(FakeTTSProvider(), StructuredLogger(log_file=None))
    audio = await module.synthesize(text)
    assert audio
