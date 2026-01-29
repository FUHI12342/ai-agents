#!/usr/bin/env python3
"""
Live Trading Reconciliation
Compare ledger with exchange data.
"""

import sys
import time
import json
from pathlib import Path
import ccxt

from .config import load_config, BASE_DIR, REPORTS_DIR
from .brokers import create_broker
from .ledger import Ledger

def classify_exception(e: Exception) -> str:
    if isinstance(e, ccxt.AuthenticationError):
        return "AUTH"
    elif isinstance(e, ccxt.RateLimitExceeded):
        return "RATE_LIMIT"
    elif isinstance(e, ccxt.InvalidNonce) or "-1021" in str(e):
        return "TIME_SKEW"
    elif isinstance(e, ccxt.NetworkError):
        return "NETWORK"
    elif isinstance(e, ccxt.ExchangeNotAvailable):
        return "EXCHANGE_DOWN"
    else:
        return "UNKNOWN"

def main():
    config = load_config()
    ts = int(time.time() * 1000)

    # For live/testnet, do full check; for paper, just record OK
    is_full_check = config.trader_mode in ('testnet', 'live')

    if is_full_check and not config.is_live_capable:
        print("[SKIP] Not configured for live trading")
        reason = "NOT_CONFIGURED_LIVE"
        result = {"ok": False, "ts": ts, "reason": reason, "details": {"error": "Not configured for live trading"}}
        exit_code = 2
    elif not is_full_check:
        # Skipped for paper or other modes
        reason = f"SKIP_MODE_{config.trader_mode.upper()}"
        result = {"ok": True, "ts": ts, "reason": reason, "details": {"mode": config.trader_mode}}
        exit_code = 0
    else:
        try:
            broker = create_broker(config)
            ledger = Ledger(REPORTS_DIR)

            # Get exchange data
            symbol = config.trader_symbols
            balance = broker.fetch_balance()
            recent_trades = broker.fetch_my_trades(symbol, limit=10) if is_full_check else []

            # Get ledger data
            ledger_trades = ledger.get_recent_trades(days=1)
            ledger_balance = ledger.get_daily_pnl()  # Simplified

            # Compare
            exchange_total_usdt = balance.get('total', {}).get('USDT', 0.0)
            exchange_total_btc = balance.get('total', {}).get('BTC', 0.0)

            discrepancies = []

            if is_full_check:
                # Check recent trades
                ledger_trade_ids = {t['trade_id'] for t in ledger_trades if t.get('trade_id')}
                exchange_trade_ids = {str(t['id']) for t in recent_trades}

                missing_in_ledger = exchange_trade_ids - ledger_trade_ids
                if missing_in_ledger:
                    discrepancies.append(f"Trades missing in ledger: {list(missing_in_ledger)}")

                missing_in_exchange = ledger_trade_ids - exchange_trade_ids
                if missing_in_exchange:
                    discrepancies.append(f"Trades missing in exchange: {list(missing_in_exchange)}")

                # Balance check (rough) - simplified
                # TODO: improve balance reconciliation

            ok = len(discrepancies) == 0
            reason = "OK" if ok else "DISCREPANCIES"
            details = {
                "mode": config.trader_mode,
                "symbol": symbol,
                "exchange_balance": {"USDT": exchange_total_usdt, "BTC": exchange_total_btc},
                "recent_trades_count": len(recent_trades),
                "ledger_trades_count": len(ledger_trades),
                "discrepancies": discrepancies,
            }
            result = {"ok": ok, "ts": ts, "reason": reason, "details": details}
            exit_code = 0 if ok else 2

        except Exception as e:
            print(f"[ERROR] Reconciliation failed: {e}")
            reason = classify_exception(e)
            result = {"ok": False, "ts": ts, "reason": reason, "details": {"error": str(e)}}
            exit_code = 2

    # Write JSON
    reconcile_json_file = REPORTS_DIR / "reconcile_latest.json"
    reconcile_json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(reconcile_json_file, 'w') as f:
        json.dump(result, f, indent=2)

    # Write TXT
    reconcile_file = REPORTS_DIR / "reconcile_latest.txt"
    with open(reconcile_file, 'w') as f:
        f.write("Live Trading Reconciliation Report\n")
        f.write(f"Timestamp: {ts}\n")
        f.write(f"OK: {result['ok']}\n")
        f.write(f"Reason: {result.get('reason', 'UNKNOWN')}\n")
        f.write(f"Mode: {result['details'].get('mode', 'unknown')}\n")
        f.write(f"Symbol: {result['details'].get('symbol', 'unknown')}\n")
        f.write("\n")
        f.write("Exchange Balance:\n")
        bal = result['details'].get('exchange_balance', {})
        f.write(f"  USDT: {bal.get('USDT', 0.0)}\n")
        f.write(f"  BTC: {bal.get('BTC', 0.0)}\n")
        f.write("\n")
        if result['details'].get('discrepancies'):
            f.write("Discrepancies:\n")
            for d in result['details']['discrepancies']:
                f.write(f"  - {d}\n")
            f.write("\n")
            f.write("ACTION REQUIRED: Check manually\n")
        else:
            f.write("No discrepancies found.\n")

    print(f"[DONE] Reconciliation completed. OK={result['ok']}. See {reconcile_file}")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()