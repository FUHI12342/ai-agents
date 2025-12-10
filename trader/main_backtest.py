from .data_loader import load_ohlcv
from .strategy import sma_crossover_signal
from .backtest import simple_backtest
from .logging_utils import append_backtest_log

def main():
    symbol = "DEMO"  # ダミーシンボル名
    df = load_ohlcv(symbol)
    df = sma_crossover_signal(df, short=5, long=20)
    stats = simple_backtest(df)

    print("=== Backtest Result ===")
    for k, v in stats.items():
        print(f"{k}: {v}")

    log_path = append_backtest_log(symbol, stats)
    print(f"\nログ保存先: {log_path}")

if __name__ == "__main__":
    main()
