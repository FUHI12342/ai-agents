import pandas as pd

from trader.ml.labels import detect_pivot_lows, detect_rebound_signals
from trader.ml.pipeline import build_signals_summary


def test_build_signals_summary_extracts_latest_entries(tmp_path):
    timestamps = pd.date_range("2024-01-01", periods=6, freq="h")
    df = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": [10, 9, 6, 5.5, 6.1, 6.5],
            "high": [10.5, 9.5, 6.2, 6.0, 6.3, 6.7],
            "low": [9.8, 8.8, 5.0, 5.3, 5.9, 6.1],
            "close": [10, 9, 5.0, 5.4, 6.2, 6.4],
            "volume": [1] * 6,
        }
    )

    df = detect_pivot_lows(df, k=1)
    df = detect_rebound_signals(df, rebound_n=3, rebound_pct=0.1)

    params = {"k": 1, "rebound_n": 3, "rebound_pct": 0.1, "last": 50}
    summary = build_signals_summary(
        df=df,
        csv_path=tmp_path / "Binance_BTCUSDT_1h.csv",
        symbol="BTCUSDT",
        interval="1h",
        params=params,
    )

    assert summary["counts"]["pivot_low"] == 1
    assert summary["counts"]["buy_signal"] == 1
    assert summary["latest_pivot_low"]["index"] == 2
    assert summary["latest_pivot_low"]["timestamp_utc"].endswith("Z")
    assert summary["latest_buy_signal"]["index"] == 4
    assert summary["latest_buy_signal"]["pivot_ref_index"] == 2
