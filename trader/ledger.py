import csv
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import BASE_DIR

class Ledger:
    def __init__(self, reports_dir: Optional[Path] = None):
        if reports_dir is None:
            reports_dir = BASE_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = reports_dir
        self.run_id = str(uuid.uuid4())[:8]  # Short ID for this run

    def _get_csv_path(self, name: str) -> Path:
        return self.reports_dir / f"live_{name}_history.csv"

    def _append_csv(self, path: Path, row: Dict[str, Any]):
        file_exists = path.exists()
        with open(path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def record_order(self, order: Dict[str, Any]):
        """Record order creation"""
        row = {
            'run_id': self.run_id,
            'timestamp': order.get('timestamp', int(time.time() * 1000)),
            'order_id': order.get('id'),
            'client_order_id': order.get('clientOrderId'),
            'symbol': order.get('symbol'),
            'type': order.get('type'),
            'side': order.get('side'),
            'amount': order.get('amount'),
            'price': order.get('price'),
            'cost': order.get('cost'),
            'filled': order.get('filled', 0.0),
            'remaining': order.get('remaining', order.get('amount', 0.0)),
            'avg_price': order.get('average', order.get('price')),
            'fee': order.get('fee', {}).get('cost', 0.0),
            'status': order.get('status'),
            'reason': order.get('reason'),
        }
        self._append_csv(self._get_csv_path('orders'), row)

    def record_trade(self, trade: Dict[str, Any]):
        """Record executed trade"""
        row = {
            'run_id': self.run_id,
            'timestamp': trade.get('timestamp', int(time.time() * 1000)),
            'trade_id': trade.get('id'),
            'order_id': trade.get('order'),
            'symbol': trade.get('symbol'),
            'type': trade.get('type'),
            'side': trade.get('side'),
            'amount': trade.get('amount'),
            'price': trade.get('price'),
            'cost': trade.get('cost'),
            'fee': trade.get('fee', {}).get('cost', 0.0),
            'fee_currency': trade.get('fee', {}).get('currency'),
        }
        self._append_csv(self._get_csv_path('trades'), row)

    def record_balance_snapshot(self, balance: Dict[str, Any], equity_quote: Optional[float] = None, equity_jpy: Optional[float] = None):
        """Record balance snapshot"""
        total_usdt = balance.get('total', {}).get('USDT', 0.0)
        total_btc = balance.get('total', {}).get('BTC', 0.0)
        row = {
            'run_id': self.run_id,
            'timestamp': balance.get('timestamp', int(time.time() * 1000)),
            'USDT_total': total_usdt,
            'BTC_total': total_btc,
            'USDT_free': balance.get('free', {}).get('USDT', 0.0),
            'BTC_free': balance.get('free', {}).get('BTC', 0.0),
            'equity_quote': equity_quote,
            'equity_jpy': equity_jpy,
        }
        self._append_csv(self._get_csv_path('balance_snapshots'), row)

    def get_recent_trades(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent trades for risk calculations"""
        trades_path = self._get_csv_path('trades')
        if not trades_path.exists():
            return []

        trades = []
        cutoff_ts = int((time.time() - days * 24 * 3600) * 1000)

        with open(trades_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['timestamp']) >= cutoff_ts:
                    # Convert strings back to appropriate types
                    row['amount'] = float(row['amount'])
                    row['price'] = float(row['price'])
                    row['cost'] = float(row['cost'])
                    row['fee'] = float(row['fee'])
                    trades.append(row)

        return trades

    def get_daily_pnl(self, config) -> float:
        """Calculate daily PnL from balance snapshots in loss_guard_ccy"""
        snapshots_path = self._get_csv_path('balance_snapshots')
        if not snapshots_path.exists():
            return 0.0

        snapshots = []
        with open(snapshots_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                snapshots.append({
                    'timestamp': int(row['timestamp']),
                    'equity_quote': float(row.get('equity_quote', 0.0)),
                    'equity_jpy': float(row.get('equity_jpy', 0.0)),
                })

        if not snapshots or not any(s['equity_quote'] or s['equity_jpy'] for s in snapshots):
            return 0.0

        # Find start of day (simplified: first snapshot today)
        today_start = int(time.time() // (24*3600) * (24*3600) * 1000)
        today_snapshots = [s for s in snapshots if s['timestamp'] >= today_start]

        if len(today_snapshots) < 2:
            return 0.0

        if config.loss_guard_ccy.upper() == "JPY":
            start_equity = today_snapshots[0]['equity_jpy']
            end_equity = today_snapshots[-1]['equity_jpy']
        else:  # USDT
            start_equity = today_snapshots[0]['equity_quote']
            end_equity = today_snapshots[-1]['equity_quote']

        return end_equity - start_equity