from typing import Any, Dict, Optional, Protocol
from abc import ABC, abstractmethod

class Broker(Protocol):
    """Base protocol for trading brokers (paper and live)"""

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data for symbol"""
        ...

    @abstractmethod
    def fetch_last_price(self, symbol: str) -> float:
        """Fetch last price for symbol"""
        ...

    @abstractmethod
    def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance"""
        ...

    @abstractmethod
    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new order"""
        ...

    @abstractmethod
    def fetch_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch order status by ID"""
        ...

    @abstractmethod
    def cancel_order(self, id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel order by ID"""
        ...

    @abstractmethod
    def fetch_my_trades(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """Fetch user's trades"""
        ...

    @abstractmethod
    def fetch_open_orders(self, symbol: Optional[str] = None) -> list[Dict[str, Any]]:
        """Fetch open orders"""
        ...