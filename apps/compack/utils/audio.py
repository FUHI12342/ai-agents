from __future__ import annotations

import io
from typing import Tuple

import numpy as np

def to_wav_bytes(audio_data: np.ndarray, sample_rate: int) -> bytes:
    """Encode numpy audio data into WAV bytes."""
    try:
        import soundfile as sf

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format="WAV")
        return buffer.getvalue()
    except ImportError:  # pragma: no cover - optional dependency
        import wave

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio_data * 32767).astype("<i2").tobytes())
        return buffer.getvalue()


def from_wav_bytes(audio_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Decode WAV bytes into numpy array and sample rate."""
    try:
        import soundfile as sf

        buffer = io.BytesIO(audio_bytes)
        data, sr = sf.read(buffer, dtype="float32")
        return data, sr
    except ImportError:  # pragma: no cover - optional dependency
        import wave

        buffer = io.BytesIO(audio_bytes)
        with wave.open(buffer, "rb") as wf:
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        data = np.frombuffer(frames, dtype="<i2").astype("float32") / 32767.0
        return data, sr
