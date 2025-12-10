import pandas as pd

def sma_crossover_signal(df: pd.DataFrame, short: int = 5, long: int = 20) -> pd.DataFrame:
    """短期/長期移動平均のクロスで売買シグナルを出す"""
    df = df.copy()
    df["sma_short"] = df["close"].rolling(short).mean()
    df["sma_long"] = df["close"].rolling(long).mean()
    df["signal"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1   # ロング
    df.loc[df["sma_short"] < df["sma_long"], "signal"] = -1  # ショート
    return df
