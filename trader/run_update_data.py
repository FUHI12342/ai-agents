#!/usr/bin/env python3
"""
Binanceデータ更新CLI
"""
import argparse
import sys
from pathlib import Path
from .data_updater import update_data
from .config import DATA_DIR

def main():
    parser = argparse.ArgumentParser(description="Update Binance OHLCV data")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--interval", default="1d", help="Interval (default: 1d)")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Data directory")

    args = parser.parse_args()

    try:
        old_last, new_last, added = update_data(args.symbol, args.interval, args.data_dir)
        print(f"Updated {args.symbol} ({args.interval})")
        print(f"Old last date: {old_last}")
        print(f"New last date: {new_last}")
        print(f"Added rows: {added}")
        return 0
    except Exception as e:
        print(f"Error updating data: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())