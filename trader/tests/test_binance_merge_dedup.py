from pathlib import Path

import pandas as pd

from trader.data_sources import binance


def test_fetch_and_update_binance_dedup(monkeypatch, tmp_path: Path):
    out_dir = tmp_path
    csv_path = out_dir / "Binance_BTCUSDT_1h.csv"

    existing = pd.DataFrame(
        [
            {"timestamp_utc": "2024-01-01T00:00:00Z", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
            {"timestamp_utc": "2024-01-01T01:00:00Z", "open": 2, "high": 3, "low": 1.5, "close": 2.5, "volume": 12},
        ]
    )
    existing.to_csv(csv_path, index=False, encoding="utf-8")

    new_df = pd.DataFrame(
        [
            {"timestamp_utc": "2024-01-01T01:00:00Z", "open": 2.1, "high": 3.1, "low": 1.6, "close": 2.6, "volume": 13},
            {"timestamp_utc": "2024-01-01T02:00:00Z", "open": 3, "high": 4, "low": 2.5, "close": 3.5, "volume": 15},
        ]
    )

    monkeypatch.setattr(binance, "fetch_all_klines", lambda symbol, interval, start_date, end_date=None: new_df)

    result_path = binance.fetch_and_update_binance(
        symbol="BTCUSDT",
        output_dir=out_dir,
        interval="1h",
        start_date="2024-01-01",
        end_date=None,
        strict=True,
    )

    assert result_path == csv_path
    merged = pd.read_csv(csv_path)
    assert len(merged) == 3
    assert merged["timestamp_utc"].tolist() == [
        "2024-01-01T00:00:00Z",
        "2024-01-01T01:00:00Z",
        "2024-01-01T02:00:00Z",
    ]
    assert merged.loc[merged["timestamp_utc"] == "2024-01-01T01:00:00Z", "close"].iloc[0] == 2.6
    assert merged["close"].iloc[-1] == 3.5
