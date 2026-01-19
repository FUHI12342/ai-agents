from __future__ import annotations

import pandas as pd


def add_ma_crossover_signals(
    df: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 100,
    price_col: str = "close",
) -> pd.DataFrame:
    """
    MAクロス戦略のシグナルを DataFrame に付与する。

    追加カラム:
      - ma_short, ma_long
      - signal:  1 = long, -1 = exit（※ショートはしない）
      - position: signal を 1日遅らせた保有状態（1=保有, 0=ノーポジ）

    注意:
      - 価格列は price_col で指定（既定 'close'）
      - run_backtest_with_risk / run_backtest_multi_assets から使う想定
    """
    out = df.copy()

    if price_col not in out.columns:
        raise ValueError(f"price_col='{price_col}' not found in columns: {list(out.columns)}")

    px = out[price_col].astype(float)

    out["ma_short"] = px.rolling(window=short_window, min_periods=short_window).mean()
    out["ma_long"] = px.rolling(window=long_window, min_periods=long_window).mean()

    out["signal"] = 0

    # ゴールデンクロス/デッドクロス判定（short/long 両方揃ってから）
    valid = out["ma_short"].notna() & out["ma_long"].notna()
    cross_up = valid & (out["ma_short"] > out["ma_long"]) & (out["ma_short"].shift(1) <= out["ma_long"].shift(1))
    cross_dn = valid & (out["ma_short"] < out["ma_long"]) & (out["ma_short"].shift(1) >= out["ma_long"].shift(1))

    out.loc[cross_up, "signal"] = 1
    out.loc[cross_dn, "signal"] = -1

    # ロングオンリーの保有状態（exitで0へ）
    pos = []
    holding = 0
    for sig in out["signal"].fillna(0).astype(int).tolist():
        if sig == 1:
            holding = 1
        elif sig == -1:
            holding = 0
        pos.append(holding)

    out["position"] = pd.Series(pos, index=out.index).shift(1).fillna(0).astype(int)

    return out