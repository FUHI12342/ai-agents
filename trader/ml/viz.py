from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


def plot_signals(df: pd.DataFrame, out_png: Path, last_n: int = 2000, symbol: str = "BTCUSDT", interval: str = "1h") -> Path:
    if last_n > 0:
        df = df.tail(last_n)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["timestamp_utc"], df["close"], label="close", color="blue")

    pivots = df[df.get("pivot_low", False)]
    if not pivots.empty:
        ax.scatter(pivots["timestamp_utc"], pivots["low"], color="orange", marker="v", label="pivot_low")

    signals = df[df.get("buy_signal", False)]
    if not signals.empty:
        ax.scatter(signals["timestamp_utc"], signals["close"], color="green", marker="^", label="buy_signal")

    ax.set_title(f"{symbol} {interval} - last {len(df)} bars - {df['timestamp_utc'].iloc[-1]}")
    ax.set_xlabel("timestamp")
    ax.set_ylabel("price")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    return out_png
