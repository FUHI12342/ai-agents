from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from trader.paper_engine_yahoo import simulate_ma_cross_yahoo


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_state(path: str, default_capital_jpy: float, jpy_per_usdt: float, symbols: List[str]) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "initial_capital_jpy": float(default_capital_jpy),
        "jpy_per_usdt": float(jpy_per_usdt),
        "symbols": {s: {
            "cash_quote": float(default_capital_jpy) / float(jpy_per_usdt),
            "pos_base": 0.0,
            "last_ts": None,
            "prev_diff": None,
            "peak_equity_quote": None,
            "max_drawdown_pct": 0.0,
            "trades_total": 0
        } for s in symbols}
    }


def save_state(path: str, st: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if not rows:
        # still write header for convenience
        header = ["time_iso","time_ms","symbol","side","price","qty","notional_quote","fee_quote","cash_quote_after","pos_base_after","equity_quote_after","equity_jpy_after","reason"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
        return

    header = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_history(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    exists = os.path.exists(path)
    header = list(rows[0].keys())
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    p = argparse.ArgumentParser(description="Yahoo daily paper trading simulation (MA cross) with trade logs + equity updates")
    p.add_argument("--capital-jpy", type=float, default=10000.0, help="Initial virtual capital in JPY")
    p.add_argument("--symbols", default="^N225", help="Comma-separated Yahoo symbols, e.g. ^N225,USDJPY=X")
    p.add_argument("--ma-short", type=int, default=20)
    p.add_argument("--ma-long", type=int, default=100)
    p.add_argument("--risk-pct", type=float, default=0.25)
    p.add_argument("--fee-rate", type=float, default=0.001)
    p.add_argument("--slippage-bps", type=float, default=10.0)
    p.add_argument("--jpy-per-usdt", type=float, default=150.0)
    p.add_argument("--state-file", default=r"D:\ai-data\paper_state_yahoo.json")
    p.add_argument("--out-dir", default=os.path.join("trader", "reports"))
    p.add_argument("--data-dir", default=r"D:\ai-data\trader\data")
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    out_dir = os.path.abspath(args.out_dir)
    data_dir = Path(args.data_dir)
    os.makedirs(out_dir, exist_ok=True)

    st = load_state(args.state_file, args.capital_jpy, args.jpy_per_usdt, symbols)
    jpy_per_usdt = float(st.get("jpy_per_usdt", args.jpy_per_usdt))

    latest_rows: List[Dict[str, Any]] = []
    summary_lines: List[str] = []
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    summary_lines.append(f"Yahoo PaperTrade Simulation (MA cross) {now}")
    summary_lines.append(f"JPY/USDT assumed: {jpy_per_usdt:.4f}")
    summary_lines.append("")

    for sym in symbols:
        sym_state_raw = st["symbols"].get(sym)
        if not sym_state_raw:
            st["symbols"][sym] = {
                "cash_quote": float(st["initial_capital_jpy"]) / jpy_per_usdt,
                "pos_base": 0.0,
                "last_ts": None,
                "prev_diff": None,
                "peak_equity_quote": None,
                "max_drawdown_pct": 0.0,
                "trades_total": 0
            }
            sym_state_raw = st["symbols"][sym]

        from trader.paper_engine import PaperState
        state = PaperState(
            cash_quote=float(sym_state_raw["cash_quote"]),
            pos_base=float(sym_state_raw["pos_base"]),
            last_ts=sym_state_raw.get("last_ts", None),
            prev_diff=sym_state_raw.get("prev_diff", None),
            peak_equity_quote=sym_state_raw.get("peak_equity_quote", None),
            max_drawdown_pct=float(sym_state_raw.get("max_drawdown_pct", 0.0)),
            trades_total=int(sym_state_raw.get("trades_total", 0)),
        )

        from trader.paper_engine_yahoo import load_yahoo_ohlcv
        try:
            data = load_yahoo_ohlcv(sym, data_dir)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            # Overwrite summary with FAIL
            summary_txt = os.path.join(out_dir, "paper_yahoo_summary_latest.txt")
            with open(summary_txt, "w", encoding="utf-8") as f:
                f.write("PaperYahoo Summary\n")
                f.write(f"ERROR: {e}\n")
                f.write(f"symbol: {sym}\n")
                f.write("reason: data file not found\n")
            return 1
        except Exception as e:
            print(f"ERROR: Failed to load data for {sym}: {e}")
            # Overwrite summary with FAIL
            summary_txt = os.path.join(out_dir, "paper_yahoo_summary_latest.txt")
            with open(summary_txt, "w", encoding="utf-8") as f:
                f.write("PaperYahoo Summary\n")
                f.write(f"ERROR: {e}\n")
                f.write(f"symbol: {sym}\n")
                f.write("reason: failed to load data\n")
                # Add debug info if available
                if isinstance(e, ValueError) and "Debug info:" in str(e):
                    debug_part = str(e).split("Debug info: ", 1)[1]
                    f.write(f"Debug info: {debug_part}\n")
            # Overwrite trades_latest with empty
            latest_csv = os.path.join(out_dir, "paper_yahoo_trades_latest.csv")
            write_csv(latest_csv, [])
            return 1

        if not data:
            print(f"ERROR: No data loaded for {sym} (candles=0)")
            # Overwrite summary with FAIL
            summary_txt = os.path.join(out_dir, "paper_yahoo_summary_latest.txt")
            with open(summary_txt, "w", encoding="utf-8") as f:
                f.write("PaperYahoo Summary\n")
                f.write("ERROR: candles=0\n")
                f.write(f"symbol: {sym}\n")
                f.write("reason: no data loaded\n")
            # Overwrite trades_latest with empty
            latest_csv = os.path.join(out_dir, "paper_yahoo_trades_latest.csv")
            write_csv(latest_csv, [])
            return 1

        # Check for state corruption: if last_ts is in the future relative to data max date
        max_date_ms = max(ts for ts, _, _, _, _, _ in data) if data else 0
        if state.last_ts and state.last_ts > max_date_ms:
            print(f"WARNING: state.last_ts {state.last_ts} > max_date {max_date_ms} for {sym}, resetting state")
            state = PaperState(
                cash_quote=float(st["initial_capital_jpy"]) / jpy_per_usdt,
                pos_base=0.0,
                last_ts=None,
                prev_diff=None,
                peak_equity_quote=None,
                max_drawdown_pct=0.0,
                trades_total=state.trades_total,  # keep trades_total cumulative
            )
            summary_lines.append(f"WARNING: state reset for {sym} due to future last_ts\n")

        before_trades_total = state.trades_total
        state, new_trades, equity_curve = simulate_ma_cross_yahoo(
            sym,
            state,
            ma_short=args.ma_short,
            ma_long=args.ma_long,
            risk_pct=args.risk_pct,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
            data_dir=data_dir,
        )

        if not equity_curve:
            print(f"ERROR: No equity curve generated for {sym} (possibly insufficient data)")
            # Overwrite summary with FAIL
            summary_txt = os.path.join(out_dir, "paper_yahoo_summary_latest.txt")
            with open(summary_txt, "w", encoding="utf-8") as f:
                f.write("PaperYahoo Summary\n")
                f.write("ERROR: equity_curve missing\n")
                f.write(f"symbol: {sym}\n")
                f.write("reason: insufficient data\n")
            # Overwrite trades_latest with empty
            latest_csv = os.path.join(out_dir, "paper_yahoo_trades_latest.csv")
            write_csv(latest_csv, [])
            return 1

        # current equity at last close (if exists)
        last_close = data[-1][4] if data else 0.0
        equity_quote = state.cash_quote + state.pos_base * last_close
        equity_jpy = equity_quote * jpy_per_usdt

        # build csv rows for this run
        for t in new_trades:
            ts_ms = int(t["time_ms"])
            row = {
                "time_iso": _iso(ts_ms),
                "time_ms": ts_ms,
                "symbol": t["symbol"],
                "side": t["side"],
                "price": float(t["price"]),
                "qty": float(t["qty"]),
                "notional_quote": float(t["notional_quote"]),
                "fee_quote": float(t["fee_quote"]),
                "cash_quote_after": float(t["cash_quote_after"]),
                "pos_base_after": float(t["pos_base_after"]),
                "equity_quote_after": (float(t["cash_quote_after"]) + float(t["pos_base_after"]) * last_close),
                "equity_jpy_after": (float(t["cash_quote_after"]) + float(t["pos_base_after"]) * last_close) * jpy_per_usdt,
                "reason": t.get("reason", ""),
            }
            latest_rows.append(row)

        # persist state
        st["symbols"][sym] = {
            "cash_quote": state.cash_quote,
            "pos_base": state.pos_base,
            "last_ts": state.last_ts,
            "prev_diff": state.prev_diff,
            "peak_equity_quote": state.peak_equity_quote,
            "max_drawdown_pct": state.max_drawdown_pct,
            "trades_total": state.trades_total,
        }

        # summary per symbol
        init_jpy = float(st["initial_capital_jpy"])
        ret_pct = (equity_jpy / init_jpy - 1.0) * 100.0 if init_jpy > 0 else 0.0
        candles = len(equity_curve) if equity_curve else 0
        last_time = _iso(equity_curve[-1][0]) if equity_curve else "(none)"
        reason = "OK"
        if not data:
            reason = "NO_DATA"
        elif not equity_curve:
            reason = "NO_EQUITY_CURVE"
        summary_lines.append(f"[{sym}] candles={candles} last={last_time} reason={reason}")
        summary_lines.append(f"- equity_jpy: {equity_jpy:,.2f}  return: {ret_pct:,.2f}%  maxDD: {state.max_drawdown_pct:,.2f}%")
        summary_lines.append(f"- cash_quote: {state.cash_quote:,.6f}  pos_base: {state.pos_base:,.6f}  new_trades: {state.trades_total - before_trades_total}")
        summary_lines.append("")

    # write outputs
    latest_csv = os.path.join(out_dir, "paper_yahoo_trades_latest.csv")
    hist_csv   = os.path.join(out_dir, "paper_yahoo_trades_history.csv")
    summary_txt = os.path.join(out_dir, "paper_yahoo_summary_latest.txt")

    write_csv(latest_csv, latest_rows)
    append_history(hist_csv, latest_rows)

    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines).rstrip() + "\n")
        f.write("\nFiles\n")
        f.write(f"- latest trades : {latest_csv}\n")
        f.write(f"- history trades: {hist_csv}\n")
        f.write(f"- state         : {os.path.abspath(args.state_file)}\n")

    save_state(args.state_file, st)

    print("\n".join(summary_lines))
    print("OK:")
    print(f"- wrote {summary_txt}")
    print(f"- wrote {latest_csv}")
    print(f"- appended {hist_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())