"""
Yahoo Finance から日足OHLCVを取得してCSV保存するユーティリティ。

使い方例:
  python -m trader.download_market_data --symbols ^GSPC ^N225
  python -m trader.download_market_data --symbols "^^GSPC" "^^N225"
  python -m trader.download_market_data --symbols ^GSPC ^N225 --strict
  python -m trader.download_market_data --symbols "^IXIC" "USDJPY=X" --start 2010-01-01 --strict
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd
import yfinance as yf

from .config import DATA_DIR
from .yahoo_symbols import symbol_to_yahoo_file_stem


def _normalize_symbol(raw: str) -> str:
    s = (raw or "").strip()
    while "^^" in s:
        s = s.replace("^^", "^")
    return s


def download_daily_ohlcv(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True, help="例: ^GSPC ^N225 BTC-USD（.batからは ^^GSPC でもOK）")
    ap.add_argument("--start", default=None, help="例: 2020-01-01")
    ap.add_argument("--end", default=None, help="例: 2025-12-31")
    ap.add_argument("--strict", action="store_true", help="1つでもDL失敗したら exit code=1（タスクスケジューラ向け）")
    args = ap.parse_args()

    print(f"[INFO] Save dir: {DATA_DIR}")

    failed: List[str] = []
    for raw in args.symbols:
        s = _normalize_symbol(raw)
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