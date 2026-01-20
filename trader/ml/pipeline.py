from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from trader.config import DATA_DIR
from trader.ml.labels import detect_pivot_lows, detect_rebound_signals
from trader.ml.viz import plot_signals


def resolve_csv_path(cli_path: Optional[str]) -> Path:
    candidates = []
    if cli_path:
        candidates.append(Path(cli_path))

    env_data_dir = os.getenv("TRADER_DATA_DIR")
    if env_data_dir:
        candidates.append(Path(env_data_dir) / "Binance_BTCUSDT_1h.csv")
    candidates.append(Path(r"D:\ai-data\trader-dev\data\Binance_BTCUSDT_1h.csv"))
    candidates.append(Path(r"D:\ai-data\trader\data\Binance_BTCUSDT_1h.csv"))
    candidates.append(Path(DATA_DIR) / "Binance_BTCUSDT_1h.csv")

    for p in candidates:
        if p and p.exists():
            return p
    return candidates[-1]


def resolve_out_png_path(cli_out: Optional[str]) -> Path:
    if cli_out:
        return Path(cli_out)
    if os.getenv("TRADER_REPORTS_DIR"):
        return Path(os.getenv("TRADER_REPORTS_DIR")) / "signals_chart_latest.png"
    default_dev = Path(r"D:\ai-data\trader-dev\reports\signals_chart_latest.png")
    if default_dev.parent.exists():
        return default_dev
    return Path("reports") / "signals_chart_latest.png"


def resolve_out_json_path(cli_out: Optional[str]) -> Path:
    if cli_out:
        return Path(cli_out)
    if os.getenv("TRADER_REPORTS_DIR"):
        return Path(os.getenv("TRADER_REPORTS_DIR")) / "signals_latest.json"
    default_dev = Path(r"D:\ai-data\trader-dev\reports\signals_latest.json")
    if default_dev.parent.exists():
        return default_dev
    return Path("reports") / "signals_latest.json"


def load_df(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "timestamp_utc" not in df.columns:
        raise ValueError("CSV must contain timestamp_utc column")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    return df


def _iso_utc(ts: Optional[pd.Timestamp]) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
        ts = ts.tz_localize(timezone.utc)
    else:
        ts = ts.tz_convert(timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_signals_summary(
    df: pd.DataFrame,
    csv_path: Path,
    symbol: str,
    interval: str,
    params: Dict,
) -> Dict:
    counts = {
        "pivot_low": int(df["pivot_low"].sum()) if "pivot_low" in df.columns else 0,
        "buy_signal": int(df["buy_signal"].sum()) if "buy_signal" in df.columns else 0,
    }

    latest_ts = df["timestamp_utc"].iloc[-1] if not df.empty else None

    latest_pivot_idx = None
    latest_pivot_row = None
    if "pivot_low" in df.columns:
        pivot_indices = df.index[df["pivot_low"]].to_list()
        if pivot_indices:
            latest_pivot_idx = pivot_indices[-1]
            latest_pivot_row = df.loc[latest_pivot_idx]

    latest_buy_idx = None
    latest_buy_row = None
    if "buy_signal" in df.columns:
        buy_indices = df.index[df["buy_signal"]].to_list()
        if buy_indices:
            latest_buy_idx = buy_indices[-1]
            latest_buy_row = df.loc[latest_buy_idx]

    summary = {
        "symbol": symbol,
        "interval": interval,
        "source_csv": str(csv_path),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_last_timestamp_utc": _iso_utc(latest_ts),
        "params": params,
        "counts": counts,
        "latest_pivot_low": {
            "index": int(latest_pivot_idx) if latest_pivot_idx is not None else None,
            "timestamp_utc": _iso_utc(latest_pivot_row["timestamp_utc"]) if latest_pivot_row is not None else None,
            "price": float(latest_pivot_row["low"]) if latest_pivot_row is not None else None,
        },
        "latest_buy_signal": {
            "index": int(latest_buy_idx) if latest_buy_idx is not None else None,
            "timestamp_utc": _iso_utc(latest_buy_row["timestamp_utc"]) if latest_buy_row is not None else None,
            "price": float(latest_buy_row["close"]) if latest_buy_row is not None else None,
            "pivot_ref_index": (
                int(latest_buy_row["pivot_ref_index"]) if latest_buy_row is not None and not pd.isna(latest_buy_row["pivot_ref_index"]) else None
            ),
        },
    }
    return summary


def write_json_atomic(payload: Dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=out_path.name, dir=str(out_path.parent))
    tmp_file = Path(tmp_path)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_file.replace(out_path)
    finally:
        if tmp_file.exists() and tmp_file != out_path:
            try:
                tmp_file.unlink()
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect pivot lows and rebound signals, output PNG chart and JSON summary")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--csv-path", help="Path to Binance CSV (Binance_<symbol>_<interval>.csv)")
    parser.add_argument("--k", type=int, default=6, help="pivot window size")
    parser.add_argument("--rebound-n", type=int, default=24, help="lookahead bars for rebound")
    parser.add_argument("--rebound-pct", type=float, default=0.003, help="rebound threshold pct (0.003 = 0.3%)")
    parser.add_argument("--last", type=int, default=2000, help="bars to plot")
    parser.add_argument("--out-png", help="output PNG path")
    parser.add_argument("--out-json", help="output JSON summary path")
    args = parser.parse_args()

    csv_path = resolve_csv_path(args.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = load_df(csv_path)
    df = detect_pivot_lows(df, k=args.k)
    df = detect_rebound_signals(df, rebound_n=args.rebound_n, rebound_pct=args.rebound_pct)

    out_png = resolve_out_png_path(args.out_png)
    plot_signals(df, out_png, last_n=args.last, symbol=args.symbol, interval=args.interval)

    params = {"k": args.k, "rebound_n": args.rebound_n, "rebound_pct": args.rebound_pct, "last": args.last}
    summary = build_signals_summary(df, csv_path, args.symbol, args.interval, params=params)
    out_json = resolve_out_json_path(args.out_json)
    write_json_atomic(summary, out_json)

    print(f"[OK] Saved chart to {out_png}")
    print(f"[OK] Saved summary to {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
