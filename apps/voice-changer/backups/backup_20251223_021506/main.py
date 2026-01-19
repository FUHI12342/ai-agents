import argparse
import sys
from voice_changer import process_audio

def main():
    parser = argparse.ArgumentParser(description="Change voice characteristics in audio files.")
    parser.add_argument("--input", required=True, help="Input WAV file")
    parser.add_argument("--output", required=True, help="Output WAV file")
    parser.add_argument("--pitch", type=float, default=1.0, help="Pitch factor (1.0 = no change)")
    args = parser.parse_args()

    try:
        process_audio(args.input, args.output, args.pitch)
        print(f"Voice changed audio saved to {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()