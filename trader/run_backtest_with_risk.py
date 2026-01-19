import sys
import json
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR, INITIAL_CAPITAL, FEE_RATE, SYMBOL
from .data_loader import load_ohlcv
from .strategy import sma_crossover_signal
from .backtest import simple_backtest
from .logging_utils import append_backtest_log

def run_backtest_with_risk(symbol: str, short_window: int, long_window: int, risk_pct: float, fee_rate: float, start_date: str = None, end_date: str = None) -> dict:
    """
    指定されたパラメータでバックテストを実行し、結果を返す。
    """
    df = load_ohlcv(symbol)
    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    df = sma_crossover_signal(df, short=short_window, long=long_window)
    stats = simple_backtest(df)

    # リスク調整（ここでは単純にリスクパーセントを考慮したポジションサイズ調整を想定）
    # 実際のリスク管理ロジックを追加可能
    adjusted_stats = stats.copy()
    adjusted_stats['risk_pct'] = risk_pct
    adjusted_stats['fee_rate'] = fee_rate

    # ログに記録
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'short_window': short_window,
        'long_window': long_window,
        'risk_pct': risk_pct,
        'fee_rate': fee_rate,
        'start_date': start_date,
        'end_date': end_date,
        **adjusted_stats
    }
    append_backtest_log(symbol, log_entry)

    return adjusted_stats

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run backtest with risk management')
    parser.add_argument('--symbol', type=str, default=SYMBOL, help='Trading symbol')
    parser.add_argument('--preset', type=str, help='Preset name')
    parser.add_argument('--list-presets', action='store_true', help='List available presets')
    parser.add_argument('--short-window', type=int, default=20, help='Short MA window')
    parser.add_argument('--long-window', type=int, default=100, help='Long MA window')
    parser.add_argument('--risk-pct', type=float, default=0.5, help='Risk percentage')
    parser.add_argument('--fee-rate', type=float, default=FEE_RATE, help='Fee rate')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')

    args = parser.parse_args()

    if args.list_presets:
        # プリセット一覧表示（仮）
        presets = {
            'current_default': {'short': 20, 'long': 100, 'risk': 0.5, 'fee': FEE_RATE},
            'good_20_100_risk_0_5': {'short': 20, 'long': 100, 'risk': 0.5, 'fee': FEE_RATE},
        }
        print("Available presets:")
        for name, params in presets.items():
            print(f"  {name}: short={params['short']}, long={params['long']}, risk={params['risk']}, fee={params['fee']}")
        return

    # プリセット適用
    if args.preset:
        presets = {
            'current_default': {'short': 20, 'long': 100, 'risk': 0.5, 'fee': FEE_RATE},
            'good_20_100_risk_0_5': {'short': 20, 'long': 100, 'risk': 0.5, 'fee': FEE_RATE},
        }
        if args.preset in presets:
            p = presets[args.preset]
            args.short_window = p['short']
            args.long_window = p['long']
            args.risk_pct = p['risk']
            args.fee_rate = p['fee']
        else:
            print(f"Unknown preset: {args.preset}")
            return

    result = run_backtest_with_risk(
        symbol=args.symbol,
        short_window=args.short_window,
        long_window=args.long_window,
        risk_pct=args.risk_pct,
        fee_rate=args.fee_rate,
        start_date=args.start_date,
        end_date=args.end_date
    )

    print(f"PresetName={args.preset or 'custom'} Symbol={args.symbol} MA short={args.short_window} long={args.long_window} Risk pct={args.risk_pct} Fee={args.fee_rate} Start={args.start_date or 'N/A'} End={args.end_date or 'N/A'}")
    print(f"Result: {result}")

if __name__ == "__main__":
    main()