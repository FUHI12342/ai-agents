import sys
from typing import Tuple

import numpy as np
import pytest
from hypothesis import given, strategies as st

from apps.compack.core import StructuredLogger
from apps.compack.modules import STTError, STTModule, STTProvider


class FakeProvider(STTProvider):
    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:  # pragma: no cover - abstract impl
        return f"text-{len(audio_data)}"


@pytest.mark.unit
def test_record_audio_with_mocked_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """録音開始/停止のユニットテスト."""
    frames_recorded = {}

    class DummySD:
        def rec(self, frames: int, samplerate: int, channels: int, dtype: str) -> np.ndarray:
            frames_recorded["frames"] = frames
            return np.zeros((frames, channels), dtype=np.float32)

        def wait(self) -> None:
            return None

    monkeypatch.setitem(sys.modules, "sounddevice", DummySD())

    logger = StructuredLogger(log_file=None)
    stt_module = STTModule(FakeProvider(), logger, sample_rate=8000, channels=1)
    audio, sr = stt_module.record_audio(duration=0.5)

    assert sr == 8000
    assert frames_recorded["frames"] == int(0.5 * 8000)
    assert isinstance(audio, np.ndarray)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcribe_returns_provider_text() -> None:
    logger = StructuredLogger(log_file=None)
    stt_module = STTModule(FakeProvider(), logger, sample_rate=16000, channels=1)

    audio = np.ones(10, dtype=np.float32)
    text = await stt_module.transcribe(audio, 16000)

    assert text.startswith("text-")


@pytest.mark.property
@given(
    audio=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=50,
    )
)
@pytest.mark.asyncio
async def test_stt_transcription_non_empty(audio: list[float]) -> None:
    """
    Feature: voice-ai-agent-compack, Property 2: STTテキスト化の非空性.
    """
    logger = StructuredLogger(log_file=None)
    stt_module = STTModule(FakeProvider(), logger, sample_rate=16000, channels=1)

    audio_array = np.array(audio, dtype=np.float32)
    text = await stt_module.transcribe(audio_array, 16000)

    assert text != ""
