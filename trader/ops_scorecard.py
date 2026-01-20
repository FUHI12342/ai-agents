from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from trader.config import DATA_DIR, LOG_DIR, REPORTS_DIR

DATE_FMT = "%Y%m%d"
GUARD_KEYWORDS = ["[GUARD]", "KILL_SWITCH", "Data anomaly", "Reconcile Failed", "reconcile failed"]


def last_n_completed_dates(days: int, include_today: bool = False) -> List[str]:
    today = datetime.now(timezone.utc).date()
    start = 0 if include_today else 1
    return [(today - timedelta(days=i)).strftime(DATE_FMT) for i in range(start, start + days)]


def parse_log_guards(logs_dir: Path, days: List[str]) -> int:
    if not logs_dir.exists():
        return 0
    day_set = set(days)
    count = 0
    for path in logs_dir.glob("*.log"):
        try:
            import re

            name_match = re.search(r"(\d{8})", path.name)
            if name_match:
                file_date = name_match.group(1)
            else:
                file_date = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(DATE_FMT)
            if file_date not in day_set:
                continue
        except Exception:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for kw in GUARD_KEYWORDS:
            count += text.count(kw)
    return count


def extract_return_pct(data: Dict) -> Optional[float]:
    for key in ("return_pct", "return", "pnl_pct"):
        if key in data:
            try:
                return float(data[key])
            except Exception:
                continue
    final_eq = data.get("final_equity")
    init_eq = data.get("initial_equity") or data.get("initial_balance") or data.get("initial_capital")
    try:
        if final_eq is not None and init_eq:
            final_eq = float(final_eq)
            init_eq = float(init_eq)
            if init_eq != 0:
                return (final_eq - init_eq) / init_eq * 100.0
    except Exception:
        return None
    return None


def load_daily_pnls(data_dir: Path, days: List[str], allowed_symbols: List[str]) -> Dict[str, float]:
    pnls: Dict[str, float] = {}
    allowed = {s.strip().upper() for s in allowed_symbols if s}
    candidates: Dict[Tuple[str, str], List[Path]] = {}
    for path in data_dir.glob("daily_*.json"):
        parts = path.stem.split("_")
        if len(parts) < 3:
            continue
        symbol = parts[1].upper()
        date = parts[2]
        if date not in days:
            continue
        if allowed and symbol not in allowed:
            continue
        candidates.setdefault((date, symbol), []).append(path)

    for (date, symbol), paths in candidates.items():
        paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in paths:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                ret = extract_return_pct(data)
                if ret is not None:
                    pnls.setdefault(date, []).append(ret)
                    break
            except Exception:
                continue

    return {d: sum(vals) / len(vals) for d, vals in pnls.items() if vals}


def compute_score(pnls: Dict[str, float], guard_triggers: int, missing_days: int) -> float:
    if not pnls:
        return -100.0
    win_rate = sum(1 for v in pnls.values() if v > 0) / len(pnls)
    avg_return = sum(pnls.values()) / len(pnls)
    score = win_rate * 50 + avg_return - guard_triggers * 10 - missing_days * 10
    return round(score, 2)


def render_txt(result: Dict) -> str:
    lines = []
    lines.append("=== Ops Scorecard ===")
    lines.append(f"Window days: {result['window_days']}")
    lines.append(f"Score: {result['score']} (threshold {result['threshold']}) => {'PASS' if result['score_pass'] else 'FAIL'}")
    lines.append(f"Guard triggers: {result['guard_triggers']}")
    lines.append(f"Missing days: {result['missing_days']}")
    lines.append(f"PNLs: {result['pnls']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute ops scorecard from daily results")
    parser.add_argument("--days", type=int, default=7, help="Lookback days (3-30)")
    parser.add_argument("--threshold", type=float, default=70.0, help="Score threshold")
    parser.add_argument("--include-today", action="store_true", help="Include today in window")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR), help="Reports dir")
    parser.add_argument("--data-dir", default=str(DATA_DIR), help="Data dir containing daily_*.json")
    parser.add_argument("--logs-dir", default=str(LOG_DIR), help="Logs dir containing .log")
    parser.add_argument("--max-guard", type=int, default=0, help="Allowed guard triggers")
    args = parser.parse_args()

    if args.days < 3 or args.days > 30:
        print("days must be between 3 and 30")
        return 3

    days = last_n_completed_dates(args.days, include_today=args.include_today)
    allowed_symbols = [s.strip().upper() for s in os.getenv("TRADER_ALLOWED_SYMBOLS", "BTCUSDT").split(",") if s.strip()]
    data_dir = Path(args.data_dir)
    logs_dir = Path(args.logs_dir)
    reports_dir = Path(args.reports_dir)

    guard_triggers = parse_log_guards(logs_dir, days)
    pnls = load_daily_pnls(data_dir, days, allowed_symbols)
    missing_days = len([d for d in days if d not in pnls])

    score = compute_score(pnls, guard_triggers, missing_days)
    score_pass = score >= args.threshold and missing_days == 0 and guard_triggers <= args.max_guard

    result = {
        "window_days": args.days,
        "threshold": args.threshold,
        "score": score,
        "score_pass": score_pass,
        "pnls": pnls,
        "missing_days": missing_days,
        "guard_triggers": guard_triggers,
        "max_guard": args.max_guard,
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime(DATE_FMT)
    latest_json = reports_dir / "ops_scorecard_latest.json"
    latest_txt = reports_dir / "ops_scorecard_latest.txt"
    dated_json = reports_dir / f"ops_scorecard_{date_str}.json"
    dated_txt = reports_dir / f"ops_scorecard_{date_str}.txt"
    for p in (latest_json, dated_json):
        p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    txt = render_txt(result)
    for p in (latest_txt, dated_txt):
        p.write_text(txt, encoding="utf-8")

    if score_pass:
        print("[OK] Score PASS")
        return 0
    print("[WARN] Score FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
