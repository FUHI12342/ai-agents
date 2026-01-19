import argparse
import sys
from .data_updater import update_data

def main():
    parser = argparse.ArgumentParser(description="Update data for multiple symbols")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols (e.g., BTCUSDT,ETHUSDT)")
    parser.add_argument("--interval", default="1d", help="Interval for data update (default: 1d)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(',')]
    exit_code = 0
    for symbol in symbols:
        try:
            old_last, new_last, added = update_data(symbol, "1d")
            print(f"Updated {symbol}: old_last={old_last} new_last={new_last} added_rows={added}")
        except Exception as e:
            print(f"Error updating {symbol}: {e}", file=sys.stderr)
            exit_code = 1
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())