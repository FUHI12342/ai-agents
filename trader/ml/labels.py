from __future__ import annotations

import numpy as np
import pandas as pd


def detect_pivot_lows(df: pd.DataFrame, k: int = 6) -> pd.DataFrame:
    """Add pivot_low and pivot_low_price columns to df."""
    if "low" not in df.columns:
        raise ValueError("DataFrame must contain 'low' column")
    lows = df["low"].to_numpy()
    pivot_flags = np.zeros(len(df), dtype=bool)
    prices = np.full(len(df), np.nan, dtype=float)
    for i in range(k, len(df) - k):
        window = lows[i - k : i + k + 1]
        if len(window) == 0:
            continue
        if lows[i] == window.min() and (lows[i] < lows[i - 1] or lows[i] < lows[i + 1]):
            pivot_flags[i] = True
            prices[i] = lows[i]
    df = df.copy()
    df["pivot_low"] = pivot_flags
    df["pivot_low_price"] = prices
    return df


def detect_rebound_signals(
    df: pd.DataFrame,
    rebound_n: int = 24,
    rebound_pct: float = 0.003,
) -> pd.DataFrame:
    """Add buy_signal, buy_price, pivot_ref_index columns."""
    if "pivot_low" not in df.columns or "pivot_low_price" not in df.columns:
        raise ValueError("run detect_pivot_lows first")
    closes = df["close"].to_numpy()
    pivot_flags = df["pivot_low"].to_numpy()
    pivot_prices = df["pivot_low_price"].to_numpy()

    buy_signal = np.zeros(len(df), dtype=bool)
    buy_price = np.full(len(df), np.nan, dtype=float)
    pivot_ref = np.full(len(df), np.nan, dtype=float)

    for i, is_pivot in enumerate(pivot_flags):
        if not is_pivot:
            continue
        p = pivot_prices[i]
        target = p * (1 + rebound_pct)
        end_idx = min(len(df), i + rebound_n + 1)
        for j in range(i + 1, end_idx):
            if closes[j] >= target:
                if not buy_signal[j]:
                    buy_signal[j] = True
                    buy_price[j] = closes[j]
                    pivot_ref[j] = i
                break

    df = df.copy()
    df["buy_signal"] = buy_signal
    df["buy_price"] = buy_price
    df["pivot_ref_index"] = pivot_ref
    return df
