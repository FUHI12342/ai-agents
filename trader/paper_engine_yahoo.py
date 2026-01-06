from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paper_engine import PaperState, simulate_ma_cross

# OHLCV: (ts_ms, open, high, low, close, volume)
OHLCV = Tuple[int, float, float, float, float, float]


def _safe_filename(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "_").replace("=", "_")


def load_yahoo_ohlcv(symbol: str, data_dir: Path = Path(r"D:\ai-data\trader\data")) -> List[OHLCV]:
    """
    Load Yahoo Finance daily CSV and convert to OHLCV list.
    Assumes CSV format: Date,Open,High,Low,Close,Adj Close,Volume
    """
    safe_symbol = _safe_filename(symbol)
    csv_path = data_dir / f"Yahoo_{safe_symbol}_d.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Yahoo CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

    ohlcv_list = []
    for _, row in df.iterrows():
        ts_ms = int(row['date'].timestamp() * 1000)
        o = float(row['open'])
        h = float(row['high'])
        l = float(row['low'])
        c = float(row['close'])
        v = float(row['volume'])
        ohlcv_list.append((ts_ms, o, h, l, c, v))

    return ohlcv_list


def simulate_ma_cross_yahoo(
    symbol: str,
    state: PaperState,
    *,
    ma_short: int,
    ma_long: int,
    risk_pct: float,
    fee_rate: float = 0.001,
    slippage_bps: float = 10.0,
    data_dir: Path = Path(r"D:\ai-data\trader\data"),
) -> Tuple[PaperState, List[Dict[str, Any]], List[Tuple[int, float]]]:
    """
    Wrapper for simulate_ma_cross using Yahoo data.
    """
    ohlcv = load_yahoo_ohlcv(symbol, data_dir)
    return simulate_ma_cross(
        ohlcv,
        state,
        ma_short=ma_short,
        ma_long=ma_long,
        risk_pct=risk_pct,
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        symbol=symbol,
    )