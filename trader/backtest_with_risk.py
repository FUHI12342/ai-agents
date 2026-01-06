import pandas as pd
import numpy as np
from .config import INITIAL_CAPITAL, RISK_CONFIG

def backtest_with_risk(df: pd.DataFrame, periods_per_year: int = 252, initial_capital: float = INITIAL_CAPITAL, fee_rate: float = 0.0005) -> dict:
    """
    リスク調整付きバックテスト
    position: 1=long, 0=out
    signal: 1=enter long, -1=exit
    """
    df = df.copy()
    if "position" not in df.columns:
        raise ValueError("df must have 'position' column")
    if "close" not in df.columns:
        raise ValueError("df must have 'close' column")

    # ポジション変化でエントリー/エグジット判定
    df["trade"] = df["position"].diff().fillna(0)
    entries = df["trade"] > 0
    exits = df["trade"] < 0

    # リスクパーセントでポジションサイズ調整
    risk_pct = RISK_CONFIG["risk_per_trade_pct"]
    # シンプルに、ポジション割合 = risk_pct (全額投資の場合 risk_pct=1)
    df["position_pct"] = df["position"] * risk_pct

    # リターンを計算
    df["ret"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position_pct"].shift(1).fillna(0) * df["ret"]

    # 手数料（エントリー/エグジットでfee_rate、ポジションサイズ考慮）
    entry_fee = entries * fee_rate * risk_pct
    exit_fee = exits * fee_rate * risk_pct
    df["fee"] = entry_fee + exit_fee
    df["strategy_ret"] -= df["fee"]

    # エクイティ
    df["equity"] = (1 + df["strategy_ret"]).cumprod() * initial_capital

    # 結果計算
    final_equity = df["equity"].iloc[-1]
    return_pct = (final_equity / initial_capital - 1) * 100
    max_drawdown_pct = ((df["equity"] - df["equity"].cummax()) / df["equity"].cummax()).min() * 100
    num_trades = int(entries.sum())  # エントリー回数

    # 年率化リターン等はperiods_per_year使用
    # 仮でシンプルに

    return {
        "final_equity": float(final_equity),
        "return_pct": float(return_pct),
        "max_drawdown_pct": float(max_drawdown_pct),
        "num_trades": num_trades,
    }