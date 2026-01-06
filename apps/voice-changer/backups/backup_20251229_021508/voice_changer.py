import os
import numpy as np
from scipy.io import wavfile

def process_audio(input_path, output_path, pitch_factor=1.0):
    """
    Process audio file with pitch shifting.
    For pitch_factor=1.0, no change (no-op).
    """
    sample_rate, data = wavfile.read(input_path)

    if pitch_factor == 1.0:
        # No-op: copy data as is
        processed_data = data
    else:
        # TODO: Implement pitch shifting for pitch_factor != 1.0
        # For now, treat as no-op
        processed_data = data

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    wavfile.write(output_path, sample_rate, processed_data)