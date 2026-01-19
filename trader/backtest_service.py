import sys
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR, INITIAL_CAPITAL, FEE_RATE, SYMBOL
from .data_loader import load_ohlcv
from .strategy import sma_crossover_signal
from .backtest import simple_backtest
from .logging_utils import append_backtest_log

def run_backtest(symbol: str, preset: str, risk_pct: float, short_window: int, long_window: int) -> dict:
    """
    指定されたパラメータでバックテストを実行し、結果を返す。
    戻り値: dict with return_pct, max_drawdown_pct, sharpe_like, trades, final_equity, ...
    """
    df = load_ohlcv(symbol)
    df = sma_crossover_signal(df, short=short_window, long=long_window)
    stats = simple_backtest(df)

    # リスク調整（ここでは単純にリスクパーセントを考慮したポジションサイズ調整を想定）
    # 実際のリスク管理ロジックを追加可能
    adjusted_stats = stats.copy()
    adjusted_stats['risk_pct'] = risk_pct
    adjusted_stats['fee_rate'] = FEE_RATE

    # ログに記録
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'preset': preset,
        'short_window': short_window,
        'long_window': long_window,
        'risk_pct': risk_pct,
        'fee_rate': FEE_RATE,
        **adjusted_stats
    }
    append_backtest_log(symbol, log_entry)

    # 正規化された結果を返す
    return {
        'return_pct': adjusted_stats['pnl'] / INITIAL_CAPITAL * 100,  # パーセント
        'max_drawdown_pct': adjusted_stats['max_drawdown'] * 100,
        'sharpe_like': adjusted_stats['sharpe'],
        'trades': adjusted_stats['num_trades_est'],
        'final_equity': adjusted_stats['final_equity']
    }

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run backtest service')
    parser.add_argument('--symbol', type=str, default=SYMBOL, help='Trading symbol')
    parser.add_argument('--preset', type=str, help='Preset name')
    parser.add_argument('--short-window', type=int, default=20, help='Short MA window')
    parser.add_argument('--long-window', type=int, default=100, help='Long MA window')
    parser.add_argument('--risk-pct', type=float, default=0.5, help='Risk percentage')

    args = parser.parse_args()

    result = run_backtest(
        symbol=args.symbol,
        preset=args.preset,
        risk_pct=args.risk_pct,
        short_window=args.short_window,
        long_window=args.long_window
    )

    print(f"Result: {result}")

if __name__ == "__main__":
    main()