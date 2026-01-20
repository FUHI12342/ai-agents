from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from trader.config import DATA_DIR, LOG_DIR, REPORTS_DIR, load_config
from trader.ops_window import discover_daily_coverage, last_n_completed_dates
from trader.ops_scorecard import parse_log_guards

DATE_FMT = "%Y%m%d"


def check_envs(env: Dict[str, str], guard_triggers: int, max_guard: int, allowed_symbols: Set[str]) -> List[str]:
    reasons: List[str] = []
    mode = env.get("TRADER_MODE", "paper").lower()
    if mode != "paper":
        reasons.append(f"TRADER_MODE must be paper (current: {mode})")
    exch_env = env.get("TRADER_EXCHANGE_ENV", "testnet").lower()
    if exch_env not in ("testnet", "live"):
        reasons.append(f"TRADER_EXCHANGE_ENV invalid: {exch_env}")
    allow_env = {s.strip().upper() for s in env.get("TRADER_ALLOWED_SYMBOLS", "BTCUSDT").split(",") if s.strip()}
    if allow_env != allowed_symbols:
        reasons.append(f"TRADER_ALLOWED_SYMBOLS must be {','.join(sorted(allowed_symbols))} (current: {','.join(sorted(allow_env)) or 'none'})")
    if guard_triggers > max_guard:
        reasons.append(f"Guard triggers {guard_triggers} exceed max_guard {max_guard}")
    return reasons


def render_txt(result: Dict) -> str:
    lines = []
    lines.append("=== Ops Gate ===")
    lines.append(f"Window days: {result['window_days']}")
    lines.append(f"Gate: {'PASS' if result['gate_pass'] else 'FAIL'} (exit_code={result['exit_code']})")
    lines.append(f"Missing days: {result['missing_days']} ({','.join(result['missing_list']) if result['missing_list'] else 'none'})")
    lines.append(f"Guard triggers: {result['guard_triggers']} (max_guard={result['max_guard']})")
    if result["reasons"]:
        lines.append("Reasons:")
        for r in result["reasons"]:
            lines.append(f"- {r}")
    return "\n".join(lines)


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser(description="Check readiness gate (paper-only)")
    parser.add_argument("--days", type=int, default=7, help="Lookback days (3-30)")
    parser.add_argument("--max-guard", type=int, default=0, help="Allowed guard triggers")
    parser.add_argument("--include-today", action="store_true", help="Include today in window")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR), help="Reports dir")
    parser.add_argument("--data-dir", default=str(DATA_DIR), help="Data dir")
    parser.add_argument("--logs-dir", default=str(LOG_DIR), help="Logs dir")
    args = parser.parse_args()

    days = last_n_completed_dates(args.days, include_today=args.include_today)
    allowed_symbols = {s.strip().upper() for s in os.getenv("TRADER_ALLOWED_SYMBOLS", "BTCUSDT").split(",") if s.strip()}

    data_dir = Path(args.data_dir)
    logs_dir = Path(args.logs_dir)
    reports_dir = Path(args.reports_dir)

    coverage = discover_daily_coverage(data_dir, args.days, args.include_today, allowed_symbols)
    missing_list = [d for d in coverage["target_days"] if d not in coverage["covered_days"]]
    missing_days = len(missing_list)

    guard_triggers = parse_log_guards(logs_dir, days)
    reasons = check_envs(os.environ, guard_triggers, args.max_guard, allowed_symbols)
    if config.kill_switch_path.exists():
        reasons.append(f"KILL_SWITCH present at {config.kill_switch_path}")
    if missing_days:
        reasons.append(f"Missing daily files for {missing_days} day(s)")

    gate_pass = not reasons
    exit_code = 0 if gate_pass else 2
    result = {
        "window_days": args.days,
        "max_guard": args.max_guard,
        "guard_triggers": guard_triggers,
        "missing_days": missing_days,
        "missing_list": missing_list,
        "gate_pass": gate_pass,
        "reasons": reasons,
        "exit_code": exit_code,
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime(DATE_FMT)
    latest_json = reports_dir / "ops_gate_latest.json"
    latest_txt = reports_dir / "ops_gate_latest.txt"
    dated_json = reports_dir / f"ops_gate_{date_str}.json"
    dated_txt = reports_dir / f"ops_gate_{date_str}.txt"
    for p in (latest_json, dated_json):
        p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    txt = render_txt(result)
    for p in (latest_txt, dated_txt):
        p.write_text(txt, encoding="utf-8")

    if gate_pass:
        print("[OK] Gate PASS")
    else:
        print("[WARN] Gate FAIL")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
