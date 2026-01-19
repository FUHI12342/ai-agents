import numpy as np
from scipy.io import wavfile

def process_audio(input_file, output_file, pitch_factor=1.0):
    """
    Process audio file to change voice characteristics.
    For P0, this is a minimal implementation that just copies the file.
    """
    # Read the input WAV file
    sample_rate, data = wavfile.read(input_file)
    
    # For P0, just copy the data (no actual processing)
    # In a real implementation, this would apply pitch shifting, etc.
    processed_data = data
    
    # Write the output WAV file
    wavfile.write(output_file, sample_rate, processed_data)