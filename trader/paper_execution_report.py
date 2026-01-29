import argparse
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import ccxt  # type: ignore
except Exception:
    ccxt = None

from trader.paper_engine import PaperState
from trader.run_paper_sim import load_state, _ccxt_symbol
from trader.config import load_config


def calculate_ma(close_prices, period):
    if len(close_prices) < period:
        return None
    return sum(close_prices[-period:]) / period


def get_latest_signal(ohlcv, ma_short, ma_long):
    if len(ohlcv) < ma_long:
        return None, None

    closes = [row[4] for row in ohlcv]
    short_ma = calculate_ma(closes, ma_short)
    long_ma = calculate_ma(closes, ma_long)

    if short_ma is None or long_ma is None:
        return None, None

    diff = short_ma - long_ma
    return diff, diff > 0


def determine_next_action(current_signal, prev_diff, has_position):
    if current_signal is None:
        return "HOLD"

    crossed_up = prev_diff is not None and prev_diff <= 0 and current_signal > 0
    crossed_down = prev_diff is not None and prev_diff >= 0 and current_signal < 0

    if crossed_up and not has_position:
        return "BUY"
    elif crossed_down and has_position:
        return "SELL"
    else:
        return "HOLD"


def main() -> int:
    p = argparse.ArgumentParser(description="Generate paper execution summary")
    p.add_argument("--state-file", default=r"D:\ai-data\paper_state.json")
    p.add_argument("--symbols", default="BTCUSDT")
    p.add_argument("--ma-short", type=int, default=20)
    p.add_argument("--ma-long", type=int, default=100)
    p.add_argument("--risk-pct", type=float, default=0.25)
    p.add_argument("--jpy-per-usdt", type=float, default=150.0)
    from .config import REPORTS_DIR
    p.add_argument("--out-dir", default=str(REPORTS_DIR))
    args = p.parse_args()

    if ccxt is None:
        print("ERROR: ccxt not installed")
        return 1

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "paper_exec_summary_latest.txt"

    st = load_state(args.state_file, 10000, args.jpy_per_usdt, symbols)
    jpy_per_usdt = st.get("jpy_per_usdt", args.jpy_per_usdt)

    ex = ccxt.binance({"enableRateLimit": True})

    lines = []
    lines.append("Paper Execution Summary")
    lines.append("=======================")
    lines.append("")

    for sym in symbols:
        sym_ccxt = _ccxt_symbol(sym)
        sym_state = st["symbols"].get(sym)
        if not sym_state:
            continue

        state = PaperState(
            cash_quote=float(sym_state["cash_quote"]),
            pos_base=float(sym_state["pos_base"]),
            last_ts=sym_state.get("last_ts"),
            prev_diff=sym_state.get("prev_diff"),
            peak_equity_quote=sym_state.get("peak_equity_quote"),
            max_drawdown_pct=float(sym_state.get("max_drawdown_pct", 0.0)),
            trades_total=int(sym_state.get("trades_total", 0)),
        )

        # Fetch latest OHLCV
        limit = args.ma_long + 10
        ohlcv = ex.fetch_ohlcv(sym_ccxt, timeframe="1h", limit=limit)
        data = [(int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])) for row in ohlcv if len(row) >= 6]

        if not data:
            lines.append(f"[{sym}] No data available")
            continue

        last_close = data[-1][4]

        # Current position
        current_position = state.pos_base

        # Calculate signal
        diff, is_above = get_latest_signal(data, args.ma_short, args.ma_long)
        last_signal = "ABOVE" if is_above else "BELOW" if diff is not None else "UNKNOWN"

        # Next action
        next_action = determine_next_action(diff, state.prev_diff, state.pos_base > 0)

        # Target position (for BUY, calculate size)
        target_position = current_position
        suggested_order_size = 0.0
        if next_action == "BUY":
            invest = state.cash_quote * args.risk_pct
            exec_price = last_close * 1.0005  # assume slippage
            suggested_order_size = invest / exec_price if exec_price > 0 else 0.0
            target_position = current_position + suggested_order_size
        elif next_action == "SELL":
            suggested_order_size = current_position
            target_position = 0.0

        # Equity
        equity_quote = state.cash_quote + state.pos_base * last_close
        equity_jpy = equity_quote * jpy_per_usdt
        init_jpy = st["initial_capital_jpy"]
        ret_pct = (equity_jpy / init_jpy - 1.0) * 100.0 if init_jpy > 0 else 0.0

        lines.append(f"[{sym}]")
        lines.append(f"  last_signal: {last_signal}")
        lines.append(f"  next_action: {next_action}")
        lines.append(f"  suggested_order_size: {suggested_order_size:.6f}")
        lines.append(f"  current_position: {current_position:.6f}")
        lines.append(f"  target_position: {target_position:.6f}")
        lines.append(f"  equity_jpy: {equity_jpy:.2f}")
        lines.append(f"  return: {ret_pct:.2f}%")
        lines.append(f"  maxDD: {state.max_drawdown_pct:.2f}%")
        lines.append(f"  trades_total: {state.trades_total}")
        lines.append("")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())