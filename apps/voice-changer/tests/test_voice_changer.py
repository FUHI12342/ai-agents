import pytest
import numpy as np
import tempfile
import os
from scipy.io import wavfile
from pathlib import Path
import importlib.util

def _load_voice_changer():
    path = Path(__file__).resolve().parents[1] / "src" / "voice_changer.py"
    spec = importlib.util.spec_from_file_location("voice_changer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

_voice_changer = _load_voice_changer()
process_audio = _voice_changer.process_audio

def test_process_audio_basic():
    """Test basic audio processing functionality."""
    # Create a temporary input WAV file
    sample_rate = 44100
    duration = 1.0  # 1 second
    frequency = 440  # A4 note
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file:
        input_path = input_file.name
        wavfile.write(input_path, sample_rate, audio_data)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # Process the audio
        process_audio(input_path, output_path, pitch_factor=1.0)
        
        # Verify the output file was created
        assert os.path.exists(output_path)
        
        # Read the output file and verify it has the same sample rate
        output_sample_rate, output_data = wavfile.read(output_path)
        assert output_sample_rate == sample_rate
        
        # For P0, the data should be identical (no processing)
        np.testing.assert_array_equal(output_data, audio_data)
        
    finally:
        # Clean up temporary files
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)