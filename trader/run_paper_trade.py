from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from typing import Any, Dict, List, Optional, Tuple

RISK_RE = re.compile(r"^(?P<prefix>[^_]+)_(?P<symbol>.+)_risk_(?P<risk>[\d_]+)\.json$", re.IGNORECASE)

@dataclass
class ReportSummary:
    symbol: str
    risk_tag: str
    path: str
    mtime: float
    final_equity: Optional[float] = None
    return_pct: Optional[float] = None
    max_dd_pct: Optional[float] = None
    num_trades: Optional[int] = None
    sharpe: Optional[float] = None
    trades_tail: List[Dict[str, Any]] = None

def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _as_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None

def _get(d: Dict[str, Any], keys: List[str]) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def _pick_first(d: Dict[str, Any], candidates: List[List[str]]) -> Any:
    for path in candidates:
        v = _get(d, path)
        if v is not None:
            return v
    return None

def _extract_trades(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    # try common keys
    for k in ["trades", "trade_log", "orders", "fills"]:
        v = d.get(k)
        if isinstance(v, list):
            # keep only dict items
            return [x for x in v if isinstance(x, dict)]
    # sometimes nested
    for path in [["result", "trades"], ["report", "trades"], ["details", "trades"]]:
        v = _get(d, path)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []

def load_summaries(report_dir: str, report_prefix: str, symbols: Optional[List[str]]) -> List[ReportSummary]:
    pattern = os.path.join(report_dir, f"{report_prefix}_*_risk_*.json")
    files = glob(pattern)
    out: List[ReportSummary] = []

    for fp in files:
        base = os.path.basename(fp)
        m = RISK_RE.match(base)
        if not m:
            continue
        sym = m.group("symbol")
        risk_tag = m.group("risk")

        if symbols and sym not in symbols:
            continue

        st = os.stat(fp)
        out.append(ReportSummary(symbol=sym, risk_tag=risk_tag, path=fp, mtime=st.st_mtime, trades_tail=[]))

    # 譛譁ｰ縺ｮ繧ゅ・蜆ｪ蜈茨ｼ亥酔荳symbol+risk_tag縺瑚､・焚縺ゅ▲縺ｦ繧よ怙譁ｰ繧呈治逕ｨ・・    out.sort(key=lambda x: x.mtime, reverse=True)
    seen: set[Tuple[str, str]] = set()
    uniq: List[ReportSummary] = []
    for r in out:
        key = (r.symbol, r.risk_tag)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    return uniq

def enrich_summary(r: ReportSummary, tail_trades: int) -> ReportSummary:
    with open(r.path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # try to locate metrics in multiple possible schemas
    r.final_equity = _as_float(_pick_first(data, [
        ["final_equity"], ["final"], ["finalEquity"],
        ["summary", "final_equity"], ["summary", "final"],
        ["result", "final_equity"], ["result", "final"],
    ]))

    r.return_pct = _as_float(_pick_first(data, [
        ["return_pct"], ["returnPct"], ["return"], 
        ["summary", "return_pct"], ["summary", "returnPct"], ["summary", "return"],
        ["result", "return_pct"], ["result", "returnPct"], ["result", "return"],
    ]))

    r.max_dd_pct = _as_float(_pick_first(data, [
        ["max_drawdown_pct"], ["maxDD"], ["max_drawdown"], 
        ["summary", "max_drawdown_pct"], ["summary", "maxDD"], ["summary", "max_drawdown"],
        ["result", "max_drawdown_pct"], ["result", "maxDD"], ["result", "max_drawdown"],
    ]))

    r.num_trades = _as_int(_pick_first(data, [
        ["num_trades"], ["trades"], ["trade_count"],
        ["summary", "num_trades"], ["summary", "trade_count"],
        ["result", "num_trades"], ["result", "trade_count"],
    ]))

    r.sharpe = _as_float(_pick_first(data, [
        ["sharpe"], ["sharpe_ratio"],
        ["summary", "sharpe"], ["summary", "sharpe_ratio"],
        ["result", "sharpe"], ["result", "sharpe_ratio"],
    ]))

    trades = _extract_trades(data)
    if trades:
        r.trades_tail = trades[-tail_trades:]
    else:
        r.trades_tail = []

    return r

def format_summary(capital: float, items: List[ReportSummary], include_trades_tail: bool) -> str:
    lines: List[str] = []
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    lines.append(f"PaperTrade Summary (from backtest reports) {now}")
    lines.append(f"Capital (virtual): {capital:,.0f} JPY")
    lines.append("")

    if not items:
        lines.append("(no matching reports found)")
        return "\n".join(lines)

    lines.append("Per-symbol summary")
    lines.append("Symbol | RiskTag | Final | Return% | MaxDD% | Sharpe | Trades | Report")
    lines.append("------|--------|------|--------|-------|--------|--------|------")

    for r in items:
        fin = "" if r.final_equity is None else f"{r.final_equity:,.2f}"
        ret = "" if r.return_pct is None else f"{r.return_pct:.4f}"
        mdd = "" if r.max_dd_pct is None else f"{r.max_dd_pct:.4f}"
        shp = "" if r.sharpe is None else f"{r.sharpe:.4f}"
        nt  = "" if r.num_trades is None else str(r.num_trades)
        lines.append(f"{r.symbol} | {r.risk_tag} | {fin} | {ret} | {mdd} | {shp} | {nt} | {os.path.basename(r.path)}")

    if include_trades_tail:
        lines.append("")
        lines.append("Trades tail (last N per report)")
        lines.append("----------------------------------------")
        for r in items:
            if not r.trades_tail:
                continue
            lines.append(f"[{r.symbol} risk={r.risk_tag}]")
            for t in r.trades_tail:
                # print compactly
                ts = t.get("time") or t.get("timestamp") or t.get("dt") or ""
                side = t.get("side") or t.get("action") or t.get("type") or ""
                price = t.get("price") or t.get("fill_price") or t.get("avg_price") or ""
                qty = t.get("qty") or t.get("amount") or t.get("size") or ""
                fee = t.get("fee") or t.get("fee_paid") or ""
                pnl = t.get("pnl") or t.get("profit") or ""
                lines.append(f"- {ts} {side} price={price} qty={qty} fee={fee} pnl={pnl}")
            lines.append("")

    return "\n".join(lines)

def main() -> int:
    p = argparse.ArgumentParser(description="Paper trade summary from generated backtest report JSONs")
    p.add_argument("--capital", type=float, default=10000.0)
    p.add_argument("--report-prefix", default="daily")
    p.add_argument("--report-dir", default=os.path.join("trader", "reports"))
    p.add_argument("--symbols", default=None, help="Comma-separated, e.g. BTCUSDT,ETHUSDT")
    p.add_argument("--out-file", default=os.path.join("trader", "reports", "paper_summary_latest.txt"))
    p.add_argument("--tail-trades", type=int, default=10)
    p.add_argument("--include-trades-tail", action="store_true")
    args = p.parse_args()

    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    os.makedirs(args.report_dir, exist_ok=True)
    items = load_summaries(args.report_dir, args.report_prefix, symbols)
    items = [enrich_summary(r, args.tail_trades) for r in items]

    text = format_summary(args.capital, items, args.include_trades_tail)

    out_path = os.path.abspath(args.out_file)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text + "\n")

    print(text)
    print(f"\nOK: wrote {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
