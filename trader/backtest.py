import pandas as pd
from .config import INITIAL_CAPITAL

def simple_backtest(df: pd.DataFrame) -> dict:
    """
    signal列を使ってシンプルなバックテストを行う。
    ・前足のsignalでポジションを持つ
    ・手数料やスリッページはとりあえず無視
    """
    df = df.copy()
    df["position"] = df["signal"].shift(1).fillna(0)  # 前の足のシグナル
    df["ret"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["ret"]
    df["equity"] = (1 + df["strategy_ret"]).cumprod() * INITIAL_CAPITAL

    final_equity = df["equity"].iloc[-1]
    pnl = final_equity - INITIAL_CAPITAL

    # おおざっぱなトレード回数推定（signalが変わった回数/2）
    num_trades = int(df["position"].diff().abs().sum() / 2)

    # Max drawdown calculation
    peak = df["equity"].cummax()
    drawdown = (df["equity"] - peak) / peak
    max_drawdown = drawdown.min()

    # Sharpe ratio (assuming daily returns, risk-free rate = 0)
    daily_returns = df["strategy_ret"].fillna(0)
    sharpe = daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0

    return {
        "final_equity": float(final_equity),
        "pnl": float(pnl),
        "num_trades_est": num_trades,
        "max_drawdown": float(max_drawdown),
        "sharpe": float(sharpe),
    }
