"""
Binance historical OHLCV data retrieval with incremental updates.

Features:
- Fetches OHLCV data from Binance public API
- Atomic writes (tmp file + rename)
- Incremental updates with 1-interval overlap
- Deduplication and chronological sorting
- ISO8601 UTC timestamp format
- Retry logic with exponential backoff
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import requests


def fetch_binance_klines(
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int,
    limit: int = 1000,
) -> List[List]:
    """Fetch klines from Binance public API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "startTime": start_time, "endTime": end_time, "limit": limit}

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                wait_time = min(retry_after, 2**attempt)
                print(f"[WARN] Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"[WARN] Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"[WARN] Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"Failed to fetch data after {max_retries} attempts: {e}")
    return []


def klines_to_dataframe(klines: List[List]) -> pd.DataFrame:
    """Convert Binance klines to DataFrame with ISO8601 UTC timestamps."""
    if not klines:
        return pd.DataFrame(columns=["timestamp_utc", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(
        klines,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

    df["open"] = pd.to_numeric(df["open"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["close"] = pd.to_numeric(df["close"])
    df["volume"] = pd.to_numeric(df["volume"])
    df["timestamp_utc"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df[["timestamp_utc", "open", "high", "low", "close", "volume"]]

    invalid = df[
        (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
    ]
    if not invalid.empty:
        print(f"[WARN] Found {len(invalid)} rows with invalid OHLCV invariants")
    return df


def read_last_timestamp(csv_path: Path) -> Optional[str]:
    """Read the last timestamp from existing CSV file."""
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path)
        if df.empty or "timestamp_utc" not in df.columns:
            return None
        return df["timestamp_utc"].iloc[-1]
    except Exception as e:
        print(f"[WARN] Failed to read last timestamp from {csv_path}: {e}")
        return None


def fetch_all_klines(symbol: str, interval: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """Fetch all klines for the given period, handling pagination."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end_date else datetime.now(timezone.utc)

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    all_klines: List[List] = []
    current_start = start_ms
    while current_start < end_ms:
        klines = fetch_binance_klines(symbol, interval, current_start, end_ms, limit=1000)
        if not klines:
            break
        all_klines.extend(klines)
        last_close_time = klines[-1][6]
        current_start = last_close_time + 1
        if len(klines) < 1000:
            break
        time.sleep(0.1)

    return klines_to_dataframe(all_klines)


def write_csv_atomic(df: pd.DataFrame, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = csv_path.with_suffix(".tmp")
    df.to_csv(tmp_path, index=False, encoding="utf-8")
    tmp_path.replace(csv_path)


def _interval_timedelta(interval: str) -> timedelta:
    unit = interval[-1]
    try:
        value = int(interval[:-1])
    except Exception:
        value = 1
    if unit == "h":
        return timedelta(hours=value)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "d":
        return timedelta(days=value)
    return timedelta(hours=1)


def fetch_and_update_binance(
    symbol: str,
    output_dir: Path,
    interval: str = "1h",
    start_date: str = "2021-01-01",
    end_date: Optional[str] = None,
    strict: bool = False,
) -> Path:
    """Fetch or update Binance OHLCV data with incremental updates."""
    csv_path = output_dir / f"Binance_{symbol}_{interval}.csv"
    last_timestamp = read_last_timestamp(csv_path)
    overlap = _interval_timedelta(interval)

    if last_timestamp:
        print(f"[INFO] Found existing data, last timestamp: {last_timestamp}")
        last_dt = datetime.strptime(last_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        fetch_start_dt = last_dt - overlap
        fetch_start = fetch_start_dt.strftime("%Y-%m-%d")
        print(f"[INFO] Fetching incremental data from {fetch_start} (overlap {interval})")
        new_df = fetch_all_klines(symbol, interval, fetch_start, end_date)
        if new_df.empty:
            print("[INFO] No new data available")
            return csv_path

        existing_df = pd.read_csv(csv_path)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["timestamp_utc"], keep="last")
        combined_df = combined_df.sort_values("timestamp_utc").reset_index(drop=True)

        if strict:
            expected_seconds = _interval_timedelta(interval).total_seconds()
            timestamps = pd.to_datetime(combined_df["timestamp_utc"])
            time_diffs = timestamps.diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > expected_seconds * 1.1]
            if not gaps.empty:
                raise ValueError(f"Data gaps detected at indices: {gaps.index.tolist()}")

        write_csv_atomic(combined_df, csv_path)
        new_rows = len(combined_df) - len(existing_df)
        print(f"[INFO] Added {new_rows} new rows, total: {len(combined_df)}")
    else:
        print(f"[INFO] No existing data, fetching from {start_date}")
        df = fetch_all_klines(symbol, interval, start_date, end_date)
        if df.empty:
            raise ValueError(f"No data fetched for {symbol}")
        write_csv_atomic(df, csv_path)
        print(f"[INFO] Fetched {len(df)} rows")

    return csv_path


def fetch_and_update_binance_1h(
    symbol: str,
    output_dir: Path,
    start_date: str = "2021-01-01",
    end_date: Optional[str] = None,
    strict: bool = False,
) -> Path:
    return fetch_and_update_binance(symbol, output_dir, interval="1h", start_date=start_date, end_date=end_date, strict=strict)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Binance OHLCV data")
    parser.add_argument("--symbol", required=True, help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--start", default="2021-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", default="1h", help="Interval (default 1h)")
    parser.add_argument("--strict", action="store_true", help="Strict mode (error on gaps)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    csv_path = fetch_and_update_binance(
        symbol=args.symbol,
        output_dir=output_dir,
        interval=args.interval,
        start_date=args.start,
        end_date=args.end,
        strict=args.strict,
    )
    print(f"[OK] Data saved to: {csv_path}")


if __name__ == "__main__":
    main()
