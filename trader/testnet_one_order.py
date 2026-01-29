#!/usr/bin/env python3
"""
Testnet One Order - Place a single minimum notional limit order on testnet.
"""

import sys
import time
import json
import argparse
import subprocess
from pathlib import Path

from .config import load_config, BASE_DIR, REPORTS_DIR
from .brokers import create_broker
from .ledger import Ledger

def main():
    parser = argparse.ArgumentParser(description='Place one testnet order')
    parser.add_argument('--symbol', default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--side', choices=['buy', 'sell'], default='buy', help='Order side')
    parser.add_argument('--min-notional', type=float, default=5.0, help='Minimum notional quote amount')
    parser.add_argument('--price-offset-bps', type=float, default=5.0, help='Price offset in bps')
    parser.add_argument('--time-in-force', default='GTC', help='Time in force')
    args = parser.parse_args()

    config = load_config()

    # Checks
    if config.trader_mode != 'testnet':
        print("[ERROR] TRADER_MODE must be testnet")
        sys.exit(1)

    if config.dry_run != 0:
        print("[ERROR] TRADER_DRY_RUN must be false (0)")
        sys.exit(1)

    if config.allow_market != 0:
        print("[ERROR] TRADER_ALLOW_MARKET must be false (0)")
        sys.exit(1)

    kill_switch = config.kill_switch_path
    if kill_switch.exists():
        print(f"[SKIP] KILL_SWITCH present: {kill_switch}")
        sys.exit(0)

    symbol = args.symbol
    side = args.side
    min_notional = args.min_notional
    price_offset_bps = args.price_offset_bps
    time_in_force = args.time_in_force

    broker = create_broker(config)
    ledger = Ledger(REPORTS_DIR)

    print(f"[ORDER] Placing {side.upper()} limit order for {min_notional} {config.quote_ccy} on {symbol}")

    # Fetch order book
    order_book = broker.fetch_order_book(symbol, limit=5)
    if side == 'buy':
        best_price = order_book['bids'][0][0]  # best bid
        price = best_price * (1 - price_offset_bps / 10000.0)
    else:
        best_price = order_book['asks'][0][0]  # best ask
        price = best_price * (1 + price_offset_bps / 10000.0)

    amount = min_notional / price

    client_order_id = f"testnet_one_{int(time.time() * 1000)}"

    print(f"[ORDER] Amount: {amount}, Price: {price}, ClientOrderId: {client_order_id}")

    # Place order
    order = broker.create_order(
        symbol,
        'limit',
        side,
        amount,
        price,
        {'clientOrderId': client_order_id, 'timeInForce': time_in_force}
    )

    ledger.record_order(order)

    print(f"[ORDER] Placed order ID: {order['id']}")

    # Wait for fill
    max_wait_sec = getattr(config, 'trader_testnet_max_wait_sec', 60)
    start_time = time.time()
    filled = 0.0
    remaining = amount

    while time.time() - start_time < max_wait_sec:
        order_status = broker.fetch_order(order['id'], symbol)
        filled = order_status.get('filled', 0.0)
        remaining = order_status.get('remaining', amount)
        status = order_status['status']

        print(f"[STATUS] {status}, Filled: {filled}, Remaining: {remaining}")

        if status == 'closed':
            # Record trades
            trades = broker.fetch_my_trades(symbol, since=order['timestamp'])
            for trade in trades:
                if trade.get('order') == order['id']:
                    ledger.record_trade(trade)
            break
        time.sleep(1)

    # Run reconcile
    print("[RECONCILE] Running reconciliation...")
    result = subprocess.run([sys.executable, '-m', 'trader.reconcile_live'], capture_output=True, text=True)
    reconcile_ok = result.returncode == 0
    reconcile_reason = 'UNKNOWN'
    reconcile_json_file = REPORTS_DIR / "reconcile_latest.json"
    if reconcile_json_file.exists():
        try:
            with open(reconcile_json_file, 'r') as f:
                rdata = json.load(f)
                reconcile_ok = rdata.get('ok', reconcile_ok)
                reconcile_reason = rdata.get('reason', reconcile_reason)
        except Exception as e:
            print(f"[ERROR] Failed to read reconcile JSON: {e}")

    # Final balance
    balance = broker.fetch_balance()

    # Write summary
    summary_file = REPORTS_DIR / "testnet_one_order_latest.txt"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, 'w') as f:
        f.write("Testnet One Order Report\n")
        f.write(f"Timestamp: {int(time.time() * 1000)}\n")
        f.write(f"Symbol: {symbol}\n")
        f.write(f"Side: {side}\n")
        f.write(f"Amount: {amount}\n")
        f.write(f"Price: {price}\n")
        f.write(f"Client Order ID: {client_order_id}\n")
        f.write(f"Order ID: {order['id']}\n")
        f.write(f"Filled: {filled}\n")
        f.write(f"Remaining: {remaining}\n")
        f.write(f"Reconcile OK: {reconcile_ok}\n")
        f.write(f"Reconcile Reason: {reconcile_reason}\n")
        f.write(f"Balance USDT: {balance.get('total', {}).get('USDT', 0.0)}\n")
        f.write(f"Balance BTC: {balance.get('total', {}).get('BTC', 0.0)}\n")

    print(f"[DONE] Testnet one order completed. See {summary_file}")

if __name__ == '__main__':
    main()