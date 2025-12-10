import os
from pathlib import Path
import numpy as np
import pandas as pd
from .config import DATA_DIR

def _generate_dummy_data(path: Path, n: int = 200):
    """データが無いとき用のダミーOHLCVを作る"""
    rng = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")
    prices = 10000 + np.cumsum(np.random.randn(n) * 100)  # 適当なランダムウォーク
    high = prices * (1 + 0.003)
    low = prices * (1 - 0.003)
    df = pd.DataFrame(
        {
            "timestamp": rng,
            "open": prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": 1000,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def load_ohlcv(symbol: str) -> pd.DataFrame:
    """シンボルのOHLCVを読み込む。なければ自動生成。"""
    path = DATA_DIR / f"{symbol}.csv"
    if not path.exists():
        _generate_dummy_data(path)

    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
