from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .config import DATA_DIR, INITIAL_CAPITAL, FEE_RATE, START_DATE, RISK_CONFIG
from .backtest_with_risk import backtest_with_risk
from .strategies.ma_crossover import add_ma_crossover_signals


DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "^GSPC", "^N225", "^IXIC", "USDJPY=X"]
REPORT_DIR = Path("trader") / "reports"


def _safe_symbol_for_filename(symbol: str) -> str:
    return symbol.replace("^", "").replace("/", "_").replace("=", "_")


def _detect_date_col(df: pd.DataFrame) -> str:
    lower = {c.lower(): c for c in df.columns}
    for cand in ["date", "datetime", "timestamp", "time"]:
        if cand in lower:
            return lower[cand]
    if "unix" in lower:
        return lower["unix"]
    return df.columns[0]


def _detect_close_col(df: pd.DataFrame) -> str:
    lower = {c.lower(): c for c in df.columns}
    # CryptoDataDownload: "Close"
    for cand in ["close", "adj close", "adj_close", "closing_price", "last"]:
        if cand in lower:
            return lower[cand]
    for c in df.columns:
        if "close" in c.lower():
            return c
    # それでも無ければ数値列から苦し紛れ
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    for c in numeric_cols:
        if all(k not in c.lower() for k in ["unix", "time", "volume", "trade"]):
            return c
    raise ValueError(f"close column not found. columns={list(df.columns)}")


def _load_binance_cryptodatadownload(symbol: str) -> pd.DataFrame:
    path = Path(DATA_DIR) / f"Binance_{symbol}_d.csv"
    if not path.exists():
        raise FileNotFoundError(f"not found: {path}")
    df = pd.read_csv(path, skiprows=1)  # 1行目のURLをskip
    return df


def _load_yahoo_from_saved_csv(symbol: str) -> pd.DataFrame:
    # download_market_data.py は Yahoo_{safe}_d.csv を作る（^ を除去）
    safe = _safe_symbol_for_filename(symbol)
    path = Path(DATA_DIR) / f"Yahoo_{safe}_d.csv"
    if not path.exists():
        raise FileNotFoundError(f"not found: {path}")
    df = pd.read_csv(path)
    return df


def load_market_data_from_local_csv(symbol: str) -> Tuple[pd.DataFrame, str]:
    """
    DATA_DIR からCSVを読む（binance/yahooをファイル名で判断）
    - BTCUSDT/ETHUSDT: Binance_{symbol}_d.csv（CryptoDataDownload形式）
    - ^GSPC/^N225/^IXIC/USDJPY=X 等: Yahoo_{safe}_d.csv
    """
    if symbol.upper().endswith("USDT"):
        df = _load_binance_cryptodatadownload(symbol)
    else:
        df = _load_yahoo_from_saved_csv(symbol)

    date_col = _detect_date_col(df)

    # unix(ms or s) の両対応
    if date_col.lower() == "unix":
        # CryptoDataDownload は ms のことが多い（例: 1765238400000）
        v = pd.to_numeric(df[date_col], errors="coerce")
        if v.dropna().astype("int64").median() > 10_000_000_000:  # 10桁超=ms寄り
            df[date_col] = pd.to_datetime(v, unit="ms", errors="coerce")
        else:
            df[date_col] = pd.to_datetime(v, unit="s", errors="coerce")
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    close_col = _detect_close_col(df)
    df["close"] = pd.to_numeric(df[close_col], errors="coerce")

    df = df.dropna(subset=[date_col, "close"]).copy()
    df = df.sort_values(date_col)
    df = df.set_index(date_col)
    return df, date_col


def _save_report_json(report_path: Path, payload: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Multi-asset backtest runner (local CSV -> MA -> backtest_with_risk)")
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--risk-pct", type=float, default=0.5)
    ap.add_argument("--ma-short", type=int, default=20)
    ap.add_argument("--ma-long", type=int, default=100)
    ap.add_argument("--report-prefix", type=str, default="daily")
    ap.add_argument("--start", type=str, default=None)
    ap.add_argument("--end", type=str, default=None)  # configに無くてもCLIで指定できる
    args = ap.parse_args()

    # START/END は config 互換を壊さないようにフォールバック
    start_s = args.start if args.start is not None else START_DATE
    # END_DATE が config.py に無い環境を想定して getattr
    end_default = getattr(__import__("trader.config", fromlist=["END_DATE"]), "END_DATE", None)
    end_s = args.end if args.end is not None else end_default

    old_risk = RISK_CONFIG.get("risk_per_trade_pct", None)
    RISK_CONFIG["risk_per_trade_pct"] = args.risk_pct

    rows: List[dict] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        for sym in args.symbols:
            try:
                df, _ = load_market_data_from_local_csv(sym)

                if start_s:
                    df = df[df.index >= pd.to_datetime(start_s)]
                if end_s:
                    df = df[df.index <= pd.to_datetime(end_s)]

                if df.empty:
                    raise ValueError("filtered data is empty")

                df = add_ma_crossover_signals(
                    df,
                    short_window=args.ma_short,
                    long_window=args.ma_long,
                    price_col="close",
                )

                # ロングオンリー（positionは関数内で作成済）
                # backtest_with_risk は df["signal"] / df["position"] を参照する実装想定
                result = backtest_with_risk(
                    df,
                    periods_per_year=365 if sym.upper().endswith("USDT") else 252,
                    initial_capital=INITIAL_CAPITAL,
                    fee_rate=FEE_RATE,
                )

                safe = _safe_symbol_for_filename(sym)
                risk_tag = str(args.risk_pct).replace(".", "_")
                report_name = f"{args.report_prefix}_{safe}_risk_{risk_tag}.json"
                report_path = REPORT_DIR / report_name

                payload = {
                    "generated_at": now,
                    "symbol": sym,
                    "ma_short": args.ma_short,
                    "ma_long": args.ma_long,
                    "risk_pct": args.risk_pct,
                    "start": start_s,
                    "end": end_s,
                    "result": result,
                }
                _save_report_json(report_path, payload)

                rows.append({
                    "symbol": sym,
                    "final_equity": float(result.get("final_equity", 0.0)),
                    "return_pct": float(result.get("return_pct", 0.0)),
                    "max_drawdown_pct": float(result.get("max_drawdown_pct", 0.0)),
                    "num_trades": int(result.get("num_trades", result.get("num_trades_est", 0))),
                    "report": report_name,
                })

            except Exception as e:
                rows.append({"symbol": sym, "error": str(e)})

    finally:
        # 元に戻す（他処理への影響を避ける）
        if old_risk is None:
            RISK_CONFIG.pop("risk_per_trade_pct", None)
        else:
            RISK_CONFIG["risk_per_trade_pct"] = old_risk

    out = pd.DataFrame(rows)

    print("=== MULTI ASSET BACKTEST ===")
    if "error" in out.columns:
        ok = out[out["error"].isna()] if out["error"].isna().any() else out[out["error"].astype(str) == "nan"]
        ng = out[out["error"].notna() & (out["error"].astype(str) != "nan")]
        if not ok.empty:
            print(ok[["symbol", "final_equity", "return_pct", "max_drawdown_pct", "num_trades", "report"]].to_string(index=False))
        if not ng.empty:
            print("\n--- ERRORS ---")
            print(ng[["symbol", "error"]].to_string(index=False))
    else:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
