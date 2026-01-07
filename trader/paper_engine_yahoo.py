from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paper_engine import PaperState, simulate_ma_cross
from .yahoo_symbols import symbol_to_yahoo_file_stem

# OHLCV: (ts_ms, open, high, low, close, volume)
OHLCV = Tuple[int, float, float, float, float, float]


def load_yahoo_ohlcv(symbol: str, data_dir: Path = Path(r"D:\ai-data\trader\data")) -> List[OHLCV]:
    """
    Load Yahoo Finance daily CSV and convert to OHLCV list.
    Assumes CSV format: Date,Open,High,Low,Close,Adj Close,Volume
    Handles 2-header CSV where second row has symbol info.
    Enhances data processing to prevent empty DataFrames.
    """
    stem = symbol_to_yahoo_file_stem(symbol)
    csv_path = data_dir / f"Yahoo_{stem}_d.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Yahoo CSV not found: {csv_path}")

    # Read first few lines for debugging
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = [f.readline().strip() for _ in range(3)]
    debug_info = {
        "csv_path": str(csv_path),
        "exists": csv_path.exists(),
        "file_size": csv_path.stat().st_size if csv_path.exists() else 0,
        "head_lines": lines,
    }

    # Check for 2-header format: if first row starts with empty cell, skip second row
    if lines and lines[0].startswith(','):
        df = pd.read_csv(csv_path, skiprows=1)
    else:
        df = pd.read_csv(csv_path)

    debug_info["columns"] = df.columns.tolist()
    debug_info["raw_dtypes"] = df.dtypes.to_dict()
    debug_info["raw_row_count"] = len(df)

    # Convert and clean data
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    df = df.dropna(subset=['date', 'open', 'high', 'low', 'close', 'volume']).sort_values('date').reset_index(drop=True)

    debug_info["processed_dtypes"] = df.dtypes.to_dict()
    debug_info["processed_row_count"] = len(df)
    debug_info["min_date"] = str(df['date'].min()) if not df.empty else None
    debug_info["max_date"] = str(df['date'].max()) if not df.empty else None

    if df.empty:
        raise ValueError(f"Loaded DataFrame is empty after processing. Debug info: {debug_info}")

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