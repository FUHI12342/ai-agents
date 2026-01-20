"""
Download market data for Yahoo (daily) or Binance (incremental) into DATA_DIR.
Binance path works without yfinance; Yahoo path requires yfinance.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from trader.config import DATA_DIR
from trader.data_sources.binance import fetch_and_update_binance
from trader.yahoo_symbols import symbol_to_yahoo_file_stem


def _normalize_symbol(raw: str) -> str:
    s = (raw or "").strip()
    while "^^" in s:
        s = s.replace("^^", "^")
    return s


def download_daily_ohlcv(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("yfinance not installed; install yfinance to fetch Yahoo data") from exc

    df = yf.download(
        tickers=symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )
    if df is None or df.empty:
        raise ValueError(f"No data returned: {symbol}")

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    df.index.name = "date"
    return df.reset_index()


def save_csv(symbol: str, df: pd.DataFrame, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"Yahoo_{symbol_to_yahoo_file_stem(symbol)}_d.csv"
    path = out_dir / fname
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def handle_binance(symbols: List[str], start: str, end: str | None, timeframe: str, strict: bool) -> int:
    failed: List[str] = []
    for s in symbols:
        try:
            csv_path = fetch_and_update_binance(
                symbol=s,
                output_dir=Path(DATA_DIR),
                interval=timeframe,
                start_date=start,
                end_date=end,
                strict=strict,
            )
            print(f"[OK] {s} updated: {csv_path}")
        except Exception as e:
            failed.append(s)
            print(f"[WARN] {s} failed: {e}")
    if failed and strict:
        print(f"[ERROR] Binance fetch failed for: {failed}")
        return 1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True, help="Symbols e.g. ^GSPC ^N225 BTCUSDT")
    ap.add_argument("--start", default=None, help="Yahoo start date YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="Yahoo end date YYYY-MM-DD")
    ap.add_argument("--strict", action="store_true", help="Fail if any symbol fails")
    ap.add_argument("--binance-start", dest="binance_start", default=None, help="Enable Binance mode with start date")
    ap.add_argument("--binance-end", dest="binance_end", default=None, help="Binance end date (optional)")
    ap.add_argument("--binance-timeframe", dest="binance_timeframe", default="1h", help="Binance timeframe (default 1h)")
    ap.add_argument("--binance-limit", dest="binance_limit", type=int, default=1000, help="Binance fetch limit (placeholder)")
    args = ap.parse_args()

    symbols = [_normalize_symbol(s) for s in args.symbols]

    if args.binance_start:
        rc = handle_binance(symbols, args.binance_start, args.binance_end, args.binance_timeframe, args.strict)
        raise SystemExit(rc)

    failed: List[str] = []
    print(f"[INFO] Save dir: {DATA_DIR}")
    for s in symbols:
        try:
            df = download_daily_ohlcv(s, start=args.start, end=args.end)
            path = save_csv(s, df, DATA_DIR)
            print(f"[OK] {s} -> {path} rows={len(df)}")
        except Exception as e:
            failed.append(s)
            print(f"[WARN] {s} failed: {e}")

    if args.strict and failed:
        print(f"[ERROR] Failed symbols: {failed}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
