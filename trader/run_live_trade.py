#!/usr/bin/env python3
"""
Live Trading Runner
One-time execution for live or paper trading.
"""

import sys
import time
from pathlib import Path

from .config import load_config, BASE_DIR
from .brokers import create_broker
from .ledger import Ledger
from .strategies.ma_cross import calculate_ma_cross_signal
from .risk_guard import check_risk_limits
from .data_loader import load_ohlcv
from .paper_engine import OHLCV
from .alert import send_alert_once
import subprocess

def main():
    config = load_config()

    # Check KILL_SWITCH
    kill_switch = config.kill_switch_path
    if kill_switch.exists():
        print(f"[SKIP] KILL_SWITCH present: {kill_switch}")
        sys.exit(0)

    # Pre-run reconcile check (for live/testnet)
    if config.trader_mode in ('testnet', 'live'):
        print("[RECONCILE] Running pre-run reconciliation...")
        result = subprocess.run([sys.executable, '-m', 'trader.reconcile_live'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Pre-run reconcile failed: {result.stderr}")
            # Alert
            send_alert_once(
                subject=f"Reconcile Failed ({config.trader_mode})",
                body=f"Pre-run reconcile failed: {result.stderr[:500]}"
            )
            # Create KILL_SWITCH
            kill_switch.write_text("Auto-created due to reconcile failure")
            print(f"[KILL] KILL_SWITCH created: {kill_switch}")
            sys.exit(2)

    # Create broker
    broker = create_broker(config)

    # Ledger
    ledger = Ledger(BASE_DIR / "reports")

    # Symbols
    symbols = [s.strip() for s in config.trader_symbols.split(',') if s.strip()]
    if not symbols:
        print("[ERROR] No symbols configured")
        sys.exit(1)

    summaries = []
    for symbol in symbols:
        print(f"[SYMBOL] Processing {symbol}")

        # Load OHLCV data (1h timeframe, assume daily run has updated data)
        try:
            df = load_ohlcv(symbol)
            # Convert to ccxt format: (ts_ms, open, high, low, close, volume)
            ohlcv = [
                (
                    int(row.timestamp.timestamp() * 1000),
                    float(row.open),
                    float(row.high),
                    float(row.low),
                    float(row.close),
                    float(row.volume),
                )
                for row in df.itertuples()
            ]
        except Exception as e:
            print(f"[ERROR] Failed to load OHLCV for {symbol}: {e}")
            continue

        if len(ohlcv) < 100:
            print(f"[ERROR] Insufficient OHLCV data for {symbol}: {len(ohlcv)}")
            continue

        # Calculate signal
        target_position, reason, _ = calculate_ma_cross_signal(ohlcv, 20, 100)
        if target_position == -1:
            print(f"[INFO] No trading signal for {symbol}")
            target_position = None  # Keep current

        # Get current position (for this symbol, approximate)
        balance = broker.fetch_balance()
        balance_quote = balance.get('total', {}).get('USDT', 0.0)
        balance_base = balance.get('total', {}).get('BTC', 0.0)  # TODO: multi-symbol position tracking

        # Calculate equity
        ticker = broker.fetch_ticker(symbol)
        last_price_quote = ticker['last']
        equity_quote = balance_quote + balance_base * last_price_quote
        equity_jpy = equity_quote * config.jpy_per_usdt

        ledger.record_balance_snapshot(balance, equity_quote, equity_jpy)

        # Approximate current position (BTC amount)  # TODO: per symbol
        current_pos = balance.get('total', {}).get('BTC', 0.0)

        # Get ticker for price
        last_price_jpy_equiv = last_price_quote * config.jpy_per_usdt

        # Determine action
        action = None
        if target_position is not None:
            if target_position == 1 and current_pos == 0.0:
                action = 'buy'
            elif target_position == 0 and current_pos > 0.0:
                action = 'sell'

        # Calculate amount and price if action
        amount = None
        price = None
        if action:
            ticker = broker.fetch_ticker(symbol)
            if action == 'buy':
                quote_balance = balance['free']['USDT']
                price = ticker['ask']
                amount = quote_balance / price * 0.99
            elif action == 'sell':
                amount = current_pos
                price = ticker['bid']

        # Risk guard
        risk_ok, risk_reason = check_risk_limits(config, ledger, broker, action, symbol, amount)
        if not risk_ok:
            print(f"[GUARD] Risk limit exceeded for {symbol}: {risk_reason}")
            if config.trader_mode in ('testnet', 'live'):
                send_alert_once(
                    subject=f"Risk Guard Triggered ({config.trader_mode})",
                    body=f"Risk limit exceeded: {risk_reason}\nMode: {config.trader_mode}\nSymbol: {symbol}\nSignal: {reason}"
                )
            # Record blocked order
            blocked_order = {
                'symbol': symbol,
                'side': action,
                'amount': amount,
                'price': price,
                'cost': amount * price if amount and price else 0.0,
                'status': 'BLOCKED_RISK',
                'reason': risk_reason,
                'timestamp': int(time.time() * 1000),
            }
            ledger.record_order(blocked_order)
            summary = {
                'symbol': symbol,
                'timestamp': int(time.time() * 1000),
                'signal': reason,
                'target_position': target_position,
                'current_position': current_pos,
                'action': action,
                'risk_guard': risk_reason,
                'order_placed': False,
                'dry_run': config.dry_run == 1,
                'balance_quote_ccy': config.quote_ccy,
                'balance_quote': balance.get('total', {}).get('USDT', 0.0),
                'balance_jpy_equiv': balance.get('total', {}).get('USDT', 0.0) * config.jpy_per_usdt,
                'last_price_quote': last_price_quote,
                'last_price_jpy_equiv': last_price_jpy_equiv,
                'balance_base': current_pos,
            }
            summaries.append(summary)
            continue
        # Live armed check for live mode
        if config.trader_mode == 'live' and not config.is_live_armed():
            print("[GUARD] Live armed check failed: confirm mismatch")
            if config.trader_mode in ('testnet', 'live'):
                send_alert_once(
                    subject=f"Live Armed Guard Triggered ({config.trader_mode})",
                    body=f"Live armed check failed: confirm mismatch\nMode: {config.trader_mode}\nSymbol: {symbol}\nSignal: {reason}"
                )
            # Record blocked order
            blocked_order = {
                'symbol': symbol,
                'side': action,
                'amount': amount,
                'price': price,
                'cost': amount * price if amount and price else 0.0,
                'status': 'BLOCKED_CONFIRM',
                'reason': 'confirm mismatch',
                'timestamp': int(time.time() * 1000),
            }
            ledger.record_order(blocked_order)
            summary = {
                'symbol': symbol,
                'timestamp': int(time.time() * 1000),
                'signal': reason,
                'target_position': target_position,
                'current_position': current_pos,
                'action': action,
                'risk_guard': 'OK',
                'blocked_confirm': True,
                'order_placed': False,
                'dry_run': config.dry_run,
                'balance_quote_ccy': config.quote_ccy,
                'balance_quote': balance.get('total', {}).get('USDT', 0.0),
                'balance_jpy_equiv': balance.get('total', {}).get('USDT', 0.0) * config.jpy_per_usdt,
                'last_price_quote': last_price_quote,
                'last_price_jpy_equiv': last_price_jpy_equiv,
                'balance_base': current_pos,
            }
            summaries.append(summary)
            continue
        # Execute order
        order_placed = False
        order = None
        dry_run_plan = None
        if action:
            try:
                ticker = broker.fetch_ticker(symbol)
                if action == 'buy':
                    # Buy with all cash
                    quote_balance = balance['free']['USDT']
                    price = ticker['ask']
                    amount = quote_balance / price * 0.99  # Leave some margin
                    order_type = 'market'
                    order_side = 'buy'
                elif action == 'sell':
                    amount = current_pos
                    price = ticker['bid']
                    order_type = 'market'
                    order_side = 'sell'

                if config.dry_run == 1:
                    # DRY_RUN: don't place order, just record plan
                    dry_run_plan = {
                        'id': f"dry_run_{int(time.time())}",
                        'symbol': symbol,
                        'type': order_type,
                        'side': order_side,
                        'amount': amount,
                        'price': price,
                        'cost': amount * price,
                        'status': 'DRY_RUN',
                        'timestamp': int(time.time() * 1000),
                    }
                    ledger.record_order(dry_run_plan)
                    order_placed = False  # Not actually placed
                    print(f"[DRY_RUN] {action.upper()} order planned: {dry_run_plan['id']}")
                else:
                    # Use safe limit order for live/testnet
                    if config.trader_mode in ('testnet', 'live'):
                        from .brokers.ccxt_live import CCXTBroker
                        if isinstance(broker, CCXTBroker):
                            order = broker.place_order_limit_safe(symbol, order_side, amount, slip_bps=10.0)
                        else:
                            order = broker.create_order(symbol, order_type, order_side, amount)
                    else:
                        order = broker.create_order(symbol, order_type, order_side, amount)
                    ledger.record_order(order)
                    order_placed = True
                    print(f"[ORDER] {action.upper()} order placed: {order['id']}")
            except Exception as e:
                print(f"[ERROR] Order failed: {e}")
                order_placed = False

        # Wait for fills if live
        if order_placed and config.trader_mode in ('testnet', 'live'):
            time.sleep(5)
            try:
                order_status = broker.fetch_order(order['id'], symbol)
                if order_status['status'] == 'closed':
                    trades = broker.fetch_my_trades(symbol, since=order['timestamp'])
                    for trade in trades:
                        if trade['order'] == order['id']:
                            ledger.record_trade(trade)
                else:
                    # Cancel if not filled
                    broker.cancel_order(order['id'], symbol)
                    print(f"[CANCEL] Order not filled, cancelled: {order['id']}")
            except Exception as e:
                print(f"[ERROR] Fill check failed: {e}")

        # Final balance
        final_balance = broker.fetch_balance()
        final_balance_quote = final_balance.get('total', {}).get('USDT', 0.0)
        final_balance_base = final_balance.get('total', {}).get('BTC', 0.0)
        final_equity_quote = final_balance_quote + final_balance_base * last_price_quote
        final_equity_jpy = final_equity_quote * config.jpy_per_usdt
        ledger.record_balance_snapshot(final_balance, final_equity_quote, final_equity_jpy)

        summary = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'signal': reason,
            'target_position': target_position,
            'current_position': current_pos,
            'action': action,
            'risk_guard': 'OK',
            'order_placed': order_placed,
            'dry_run': config.dry_run == 1,
            'balance_quote_ccy': config.quote_ccy,
            'balance_quote': final_balance.get('total', {}).get('USDT', 0.0),
            'balance_jpy_equiv': final_balance.get('total', {}).get('USDT', 0.0) * config.jpy_per_usdt,
            'last_price_quote': last_price_quote,
            'last_price_jpy_equiv': last_price_jpy_equiv,
            'balance_base': final_balance.get('total', {}).get('BTC', 0.0),
        }
        summaries.append(summary)

    # Post-run reconcile (for live/testnet)
    reconcile_ok = None
    reconcile_reason = None
    if config.trader_mode in ('testnet', 'live'):
        print("[RECONCILE] Running post-run reconciliation...")
        result = subprocess.run([sys.executable, '-m', 'trader.reconcile_live'], capture_output=True, text=True)
        reconcile_ok = result.returncode == 0
        if not reconcile_ok:
            print(f"[WARN] Post-run reconcile failed: {result.stderr}")
            # Optionally create KILL_SWITCH, but for now just warn
        # Read reconcile_latest.json for reason
        reconcile_json_file = BASE_DIR / "reports" / "reconcile_latest.json"
        if reconcile_json_file.exists():
            try:
                with open(reconcile_json_file, 'r') as f:
                    data = json.load(f)
                    reconcile_ok = data.get('ok', reconcile_ok)
                    reconcile_reason = data.get('reason', 'UNKNOWN')
            except Exception as e:
                print(f"[ERROR] Failed to read reconcile JSON: {e}")

    # Add reconcile result to summary
    summary['reconcile_ok'] = reconcile_ok
    summary['reconcile_reason'] = reconcile_reason

    # Write summary
    summary_file = BASE_DIR / "reports" / "live_summary_latest.txt"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, 'w') as f:
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")

    print("[DONE] Live trade run completed")

if __name__ == '__main__':
    main()