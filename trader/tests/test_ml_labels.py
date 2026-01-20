from pathlib import Path

import pandas as pd

from trader.ml.labels import detect_pivot_lows, detect_rebound_signals


def test_pivot_and_rebound_detection():
    data = {
        "timestamp_utc": pd.date_range("2024-01-01", periods=10, freq="h"),
        "open": [10, 9, 8, 7, 6, 7, 8, 9, 10, 11],
        "high": [11, 10, 9, 8, 7, 8, 9, 10, 11, 12],
        "low": [9, 8, 7, 6, 5, 6, 7, 8, 9, 10],
        "close": [10, 9, 8, 6.5, 5.1, 7, 8.5, 9.2, 10.5, 11],
        "volume": [1] * 10,
    }
    df = pd.DataFrame(data)

    df = detect_pivot_lows(df, k=2)
    pivot_indices = df.index[df["pivot_low"]].tolist()
    assert pivot_indices == [4]

    df = detect_rebound_signals(df, rebound_n=3, rebound_pct=0.1)
    signal_indices = df.index[df["buy_signal"]].tolist()
    assert signal_indices == [5]
