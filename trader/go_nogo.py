#!/usr/bin/env python3
"""
Go/No-Go checklist automation for live trading readiness.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List

from .config import load_config, BASE_DIR

def load_history() -> List[Dict[str, Any]]:
    """Load go_nogo history from CSV."""
    history_file = BASE_DIR / "reports" / "go_nogo_history.csv"
    if not history_file.exists():
        return []
    with open(history_file, 'r', encoding='utf-8') as f:
        import csv
        reader = csv.DictReader(f)
        return list(reader)

def get_consecutive_passes(mode: str, history: List[Dict[str, Any]]) -> int:
    """Get consecutive passes for a given mode (last 3)."""
    mode_upper = mode.upper()
    mode_entries = [h for h in history if f'READY_{mode_upper}:' in h.get('summary', '')]
    # Sort by timestamp descending
    mode_entries.sort(key=lambda x: int(x.get('timestamp', 0)), reverse=True)
    recent_entries = mode_entries[:3]
    count = 0
    for entry in recent_entries:
        if 'True' in entry.get('summary', ''):
            count += 1
        else:
            break  # Stop on first False
    return count

def check_go_nogo() -> Dict[str, Any]:
    """
    Perform go/no-go checks and return results.
    """
    config = load_config()
    reports_dir = BASE_DIR / "reports"
    results = {
        "timestamp": int(time.time() * 1000),
        "ready": False,
        "checks": {},
        "notes": {},
    }

    # 1) Order management: ledgerが存在し、直近N件に status がある
    orders_csv = reports_dir / "live_orders_history.csv"
    order_management_ok = False
    if orders_csv.exists():
        import csv
        with open(orders_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if len(rows) > 0:
                # Check if any row has status
                has_status = any(row.get('status') for row in rows[-10:])  # Last 10
                order_management_ok = has_status
    results["checks"]["order_management"] = order_management_ok

    # 2) Reconcile: paper時は SKIP (PASS), testnet/liveでapi_configured=False時は SKIP (PASS), それ以外は reconcile_latest.json ok=true
    reconcile_ok = False
    if config.trader_mode == 'paper' or not config.is_api_configured():
        reconcile_ok = True  # SKIP equivalent (PASS)
    else:
        reconcile_json = reports_dir / "reconcile_latest.json"
        if reconcile_json.exists():
            with open(reconcile_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                reconcile_ok = data.get("ok", False)
        else:
            reconcile_ok = False
    results["checks"]["reconcile"] = reconcile_ok

    # 3) Risk guard: live_summary_latest.txt の risk_guard が OK/None ならPASS
    summary_txt = reports_dir / "live_summary_latest.txt"
    risk_guard_ok = False
    if summary_txt.exists():
        with open(summary_txt, 'r', encoding='utf-8') as f:
            content = f.read()
            if "risk_guard:" in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith("risk_guard:"):
                        value = line.split(":", 1)[1].strip()
                        risk_guard_ok = value in ("OK", "None")
                        break
    results["checks"]["risk_guard"] = risk_guard_ok

    # 4) Operations: scripts/logs の最新 daily_run_*.log を1つ取得
    #     そのログに "[STEP] ops_cleanup" と "[GUARD] ops_cleanup done" が含まれていれば PASS
    #     logs が存在しない/grep不一致なら FAIL
    #     直近24時間以内の log を対象にする
    logs_dir = BASE_DIR.parent / "scripts" / "logs"
    ops_ok = False
    if logs_dir.exists():
        recent_logs = sorted(logs_dir.glob("daily_run_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        now = time.time()
        for log_file in recent_logs:
            if now - log_file.stat().st_mtime < 24 * 3600:  # Last 24 hours
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "[STEP] ops_cleanup" in content and "[GUARD] ops_cleanup done" in content:
                        ops_ok = True
                        break
            else:
                break  # Since sorted by mtime descending, no need to check older ones
    results["checks"]["operations"] = ops_ok

    # 5) Paper yahoo: paper_yahoo_summary_latest.txt exists and updated within 24h, and all symbols have valid data (candles>0 and last not none)
    paper_yahoo_summary = reports_dir / "paper_yahoo_summary_latest.txt"
    paper_yahoo_ok = False
    if paper_yahoo_summary.exists():
        now = time.time()
        mtime = paper_yahoo_summary.stat().st_mtime
        if now - mtime < 24 * 3600:
            # Parse summary to check data validity
            with open(paper_yahoo_summary, 'r', encoding='utf-8') as f:
                content = f.read()
            # Look for lines like "[sym] candles=X last=Y reason=Z"
            import re
            symbol_lines = re.findall(r'^\[([^\]]+)\] candles=(\d+) last=(.+?) reason=(\w+)', content, re.MULTILINE)
            if symbol_lines:
                all_valid = True
                for sym, candles_str, last, reason in symbol_lines:
                    candles = int(candles_str)
                    if candles <= 0 or last == "(none)" or reason != "OK":
                        all_valid = False
                        break
                if all_valid:
                    paper_yahoo_ok = True
    results["checks"]["paper_yahoo"] = paper_yahoo_ok

    # 6) API configured: for testnet/live modes
    api_configured = config.is_api_configured()
    results["checks"]["api_configured"] = api_configured

    # Load history and calculate consecutive passes
    history = load_history()
    consecutive_pass = get_consecutive_passes(config.trader_mode, history)
    results["consecutive_pass"] = consecutive_pass

    # Determine overall readiness
    checks = results["checks"]
    if not config.is_api_configured() and config.trader_mode in ('testnet', 'live'):
        results["ready"] = False
        remaining_to_go = 3  # API設定が最優先
        results["summary"] = f"READY_{config.trader_mode.upper()}: False (api_not_configured, remaining={remaining_to_go})"
    else:
        if config.trader_mode == 'paper':
            results["ready"] = checks["order_management"] and checks["operations"]
        elif config.trader_mode in ('testnet', 'live'):
            results["ready"] = consecutive_pass >= 3
        else:
            results["ready"] = False
        remaining_to_go = max(0, 3 - consecutive_pass)
        results["summary"] = f"READY_{config.trader_mode.upper()}: {results['ready']} (consecutive_pass={consecutive_pass}/3, remaining={remaining_to_go})"
    results["remaining_to_go"] = remaining_to_go

    return results

def main() -> int:
    try:
        config = load_config()
        results = check_go_nogo()

        # Write latest
        latest_file = BASE_DIR / "reports" / "go_nogo_latest.txt"
        latest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(latest_file, 'w') as f:
            f.write("Go/No-Go Checklist Results\n")
            f.write(f"Timestamp: {results['timestamp']}\n")
            f.write(f"Summary: {results['summary']}\n\n")
            f.write("Checks:\n")
            for k, v in results['checks'].items():
                f.write(f"  {k}: {'PASS' if v else 'FAIL'}\n")

            f.write("\nNext Steps:\n")
            if results.get('ready', False):
                f.write("- All checks pass. Ready for next phase.\n")
            else:
                failing_checks = [k for k, v in results['checks'].items() if not v]
                # Prioritize API configuration
                if 'api_configured' in failing_checks:
                    required_keys = []
                    if config.trader_mode == 'testnet':
                        required_keys = ['BINANCE_TESTNET_API_KEY', 'BINANCE_TESTNET_API_SECRET']
                    elif config.trader_mode == 'live':
                        required_keys = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
                    f.write(f"- Set API keys in .env: {required_keys[0]} and {required_keys[1]} (mode={config.trader_mode})\n")
                for check in failing_checks:
                    if check == 'order_management':
                        f.write("- Fix order_management: Ensure ledger has recent orders with status.\n")
                    elif check == 'reconcile':
                        if config.trader_mode != 'paper' and config.is_api_configured():
                            f.write("- Run reconcile_live to fix reconciliation.\n")
                    elif check == 'risk_guard':
                        f.write("- Fix risk_guard: Check currency units in daily loss calculation.\n")
                    elif check == 'operations':
                        f.write("- Ensure ops_cleanup and lock release in daily_run logs.\n")
                    elif check == 'paper_yahoo':
                        f.write("- Fix paper_yahoo: Ensure paper_yahoo_sim runs successfully.\n")
                    # api_configured already handled above

        # Write history (CSV)
        history_file = BASE_DIR / "reports" / "go_nogo_history.csv"
        history_exists = history_file.exists()
        with open(history_file, 'a', newline='') as f:
            import csv
            writer = csv.writer(f)
            if not history_exists:
                writer.writerow(["timestamp", "summary"] + sorted(results['checks'].keys()))
            row = [results['timestamp'], results['summary']] + list(results['checks'].values())
            writer.writerow(row)

        print(f"[DONE] Go/No-Go check completed. See {latest_file}")
        return 0
    except Exception as e:
        config = load_config()
        timestamp = int(time.time() * 1000)
        latest_file = BASE_DIR / "reports" / "go_nogo_latest.txt"
        latest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(latest_file, 'w') as f:
            f.write("Go/No-Go Checklist Results\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Summary: ERROR: {e}\n\n")
            f.write("Checks: N/A (exception occurred)\n")
            f.write("\nNext Steps:\n")
            f.write("- Fix the exception in go_nogo.py\n")

        # Write history (CSV) - minimal
        history_file = BASE_DIR / "reports" / "go_nogo_history.csv"
        history_exists = history_file.exists()
        with open(history_file, 'a', newline='') as f:
            import csv
            writer = csv.writer(f)
            if not history_exists:
                writer.writerow(["timestamp", "summary", "api_configured", "operations", "order_management", "paper_yahoo", "reconcile", "risk_guard"])
            row = [timestamp, f"ERROR: {e}", False, False, False, False, False, False]
            writer.writerow(row)

        print(f"[ERROR] Go/No-Go check failed: {e}. See {latest_file}")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())