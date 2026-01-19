import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from decimal import Decimal

from ..config import BASE_DIR, FEE_RATE, TraderConfig
from .base import Broker

class PaperState:
    def __init__(self, state_file: Path, initial_quote_balance: float):
        self.state_file = state_file
        self.cash_quote = initial_quote_balance
        self.pos_base = 0.0
        self.last_ts: Optional[int] = None
        self.prev_diff: Optional[float] = None
        self.peak_equity_quote = initial_quote_balance
        self.max_drawdown_pct = 0.0
        self.trades_total = 0
        self.load()

    def load(self):
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.cash_quote = data.get('cash_quote', self.cash_quote)
                self.pos_base = data.get('pos_base', self.pos_base)
                self.last_ts = data.get('last_ts')
                self.prev_diff = data.get('prev_diff')
                self.peak_equity_quote = data.get('peak_equity_quote', self.peak_equity_quote)
                self.max_drawdown_pct = data.get('max_drawdown_pct', self.max_drawdown_pct)
                self.trades_total = data.get('trades_total', self.trades_total)

    def save(self):
        data = {
            'cash_quote': self.cash_quote,
            'pos_base': self.pos_base,
            'last_ts': self.last_ts,
            'prev_diff': self.prev_diff,
            'peak_equity_quote': self.peak_equity_quote,
            'max_drawdown_pct': self.max_drawdown_pct,
            'trades_total': self.trades_total,
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

class PaperBroker(Broker):
    def __init__(self, config: TraderConfig, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path(r"D:\ai-data\trader\paper_state_live_mvp.json")
        initial_quote_balance = config.initial_quote_balance(config.trader_symbols)
        self.state = PaperState(state_file, initial_quote_balance)
        self.ticker_cache: Dict[str, Dict[str, Any]] = {}

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        # Return cached or default
        if symbol in self.ticker_cache:
            return self.ticker_cache[symbol]

        # Default ticker
        now = int(time.time() * 1000)
        ticker = {
            'symbol': symbol,
            'timestamp': now,
            'last': 100000.0,  # BTCUSDT price
            'bid': 99990.0,
            'ask': 100010.0,
            'bidVolume': 1.0,
            'askVolume': 1.0,
        }
        self.ticker_cache[symbol] = ticker
        return ticker

    def fetch_last_price(self, symbol: str) -> float:
        ticker = self.fetch_ticker(symbol)
        return float(ticker['last'])

    def set_ticker_price(self, symbol: str, price: float, spread_bps: float = 10.0):
        """Helper to set ticker price for testing"""
        spread = price * spread_bps / 10000.0
        self.ticker_cache[symbol] = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'last': price,
            'bid': price - spread,
            'ask': price + spread,
            'bidVolume': 1.0,
            'askVolume': 1.0,
        }

    def fetch_balance(self) -> Dict[str, Any]:
        # Simulate balance in quote currency (USDT)
        return {
            'info': {},
            'timestamp': int(time.time() * 1000),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'USDT': {
                'free': self.state.cash_quote,
                'used': 0.0,
                'total': self.state.cash_quote,
            },
            'BTC': {
                'free': self.state.pos_base,
                'used': 0.0,
                'total': self.state.pos_base,
            },
            'free': {'USDT': self.state.cash_quote, 'BTC': self.state.pos_base},
            'used': {'USDT': 0.0, 'BTC': 0.0},
            'total': {'USDT': self.state.cash_quote, 'BTC': self.state.pos_base},
        }

    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ticker = self.fetch_ticker(symbol)

        if type == 'market':
            if side == 'buy':
                exec_price = ticker['ask']
            elif side == 'sell':
                exec_price = ticker['bid']
            else:
                raise ValueError(f"Invalid side: {side}")

            notional = amount * exec_price
            fee = notional * FEE_RATE

            if side == 'buy':
                if self.state.cash_quote < notional + fee:
                    raise ValueError("Insufficient funds")
                self.state.cash_quote -= (notional + fee)
                self.state.pos_base += amount
            elif side == 'sell':
                if self.state.pos_base < amount:
                    raise ValueError("Insufficient position")
                self.state.pos_base -= amount
                self.state.cash_quote += (notional - fee)

            self.state.trades_total += 1
            order_id = f"paper_{self.state.trades_total}"

            order = {
                'id': order_id,
                'clientOrderId': None,
                'timestamp': ticker['timestamp'],
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ticker['timestamp']/1000)),
                'lastTradeTimestamp': ticker['timestamp'],
                'symbol': symbol,
                'type': type,
                'side': side,
                'amount': amount,
                'price': exec_price,
                'cost': notional,
                'average': exec_price,
                'filled': amount,
                'remaining': 0.0,
                'status': 'closed',
                'fee': {'cost': fee, 'currency': 'USDT'},
                'trades': [],
                'info': {},
            }
        else:
            raise ValueError(f"Unsupported order type: {type}")

        self.state.save()
        return order

    def fetch_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        # Paper orders are always closed immediately
        raise NotImplementedError("Paper orders are immediate, no fetch needed")

    def cancel_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        # Paper orders cannot be cancelled
        raise NotImplementedError("Paper orders are immediate, no cancel needed")

    def fetch_my_trades(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        # Return empty for paper trading
        return []

    def fetch_open_orders(self, symbol: Optional[str] = None) -> list[Dict[str, Any]]:
        # No open orders in paper trading
        return []