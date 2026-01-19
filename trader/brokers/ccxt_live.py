import time
import ccxt
from typing import Any, Dict, Optional

from ..config import TraderConfig
from .base import Broker

class CCXTBroker(Broker):
    def __init__(self, config: TraderConfig):
        self.config = config
        exchange_class = getattr(ccxt, config.ccxt_exchange)
        self.exchange = exchange_class({
            'apiKey': config.ccxt_api_key,
            'secret': config.ccxt_api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 5000,
            },
        })
        if config.ccxt_sandbox:
            try:
                self.exchange.set_sandbox_mode(True)
            except:
                pass  # Not all exchanges support sandbox
        self.time_diff_loaded = False

    def _load_time_diff_once(self):
        if not self.time_diff_loaded:
            try:
                self.exchange.load_time_difference()
                self.time_diff_loaded = True
            except Exception as e:
                print(f"[WARNING] Failed to load time difference: {e}")

    def _retry_request(self, func, *args, **kwargs):
        """Retry with exponential backoff"""
        last_exception = None
        for attempt in range(self.config.retry_max + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_max:
                    wait_time = self.config.retry_base_sec * (2 ** attempt)
                    time.sleep(wait_time)
        raise last_exception

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self._retry_request(self.exchange.fetch_ticker, symbol)

    def fetch_last_price(self, symbol: str) -> float:
        ticker = self.fetch_ticker(symbol)
        return float(ticker['last'])

    def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        return self._retry_request(self.exchange.fetch_order_book, symbol, limit)

    def fetch_balance(self) -> Dict[str, Any]:
        self._load_time_diff_once()
        return self._retry_request(self.exchange.fetch_balance)

    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self._load_time_diff_once()
        params = params or {}
        if type == 'market' and self.config.allow_market == 0:
            raise ValueError("Market orders are disabled. Use ALLOW_MARKET=1 to enable.")
        return self._retry_request(
            self.exchange.create_order,
            symbol, type, side, amount, price, params
        )

    def fetch_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        return self._retry_request(self.exchange.fetch_order, id, symbol)

    def cancel_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        return self._retry_request(self.exchange.cancel_order, id, symbol)

    def fetch_my_trades(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        return self._retry_request(self.exchange.fetch_my_trades, symbol, since, limit)

    def fetch_open_orders(self, symbol: Optional[str] = None) -> list[Dict[str, Any]]:
        return self._retry_request(self.exchange.fetch_open_orders, symbol)

    def place_order_limit_safe(
        self,
        symbol: str,
        side: str,
        amount: float,
        slip_bps: float = 10.0,
        max_wait_sec: int = 30,
        max_retry: int = 3
    ) -> Dict[str, Any]:
        """Place limit order with slippage, wait, cancel/retry logic"""
        order_book = self.fetch_order_book(symbol, 5)
        if side == 'buy':
            best_price = order_book['asks'][0][0]  # best ask
            limit_price = best_price * (1 + slip_bps / 10000.0)
        elif side == 'sell':
            best_price = order_book['bids'][0][0]  # best bid
            limit_price = best_price * (1 - slip_bps / 10000.0)
        else:
            raise ValueError(f"Invalid side: {side}")

        for attempt in range(max_retry + 1):
            try:
                # Create limit order
                order = self.create_order(symbol, 'limit', side, amount, limit_price)
                order_id = order['id']

                # Wait for fill
                start_time = time.time()
                while time.time() - start_time < max_wait_sec:
                    order_status = self.fetch_order(order_id, symbol)
                    if order_status['status'] == 'closed':
                        return order_status  # filled
                    time.sleep(1)

                # Timeout: cancel
                self.cancel_order(order_id, symbol)
                print(f"[CANCEL] Order {order_id} not filled, cancelled. Attempt {attempt+1}")

                # Update price and retry
                order_book = self.fetch_order_book(symbol, 5)
                if side == 'buy':
                    best_price = order_book['asks'][0][0]
                    limit_price = best_price * (1 + slip_bps / 10000.0)
                else:
                    best_price = order_book['bids'][0][0]
                    limit_price = best_price * (1 - slip_bps / 10000.0)

            except Exception as e:
                print(f"[ERROR] Order attempt {attempt+1} failed: {e}")
                if attempt == max_retry:
                    raise

        raise Exception(f"Order failed after {max_retry+1} attempts")