"""
Base interfaces and data structures for the strategy plugin system.

This module defines the core Strategy Protocol interface and StrategyResult dataclass
that all trading strategies must implement and return.
"""

from typing import Protocol, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class StrategyResult:
    """
    Result object returned by strategy compute methods.
    
    Attributes:
        signal: Trading signal (-1=sell, 0=hold, 1=buy)
        entry: Recommended entry price level (optional)
        stop: Stop loss level (optional)
        confidence: Signal strength (0.0-1.0)
        meta: Additional metadata including reasons and indicators
    """
    signal: int                    # -1=sell, 0=hold, 1=buy
    entry: Optional[float]         # recommended entry price
    stop: Optional[float]          # stop loss level
    confidence: float              # signal strength 0.0-1.0
    meta: Dict[str, Any]          # reasons, indicators, etc.
    
    def __post_init__(self):
        """Validate StrategyResult fields after initialization."""
        if self.signal not in [-1, 0, 1]:
            raise ValueError(f"signal must be -1, 0, or 1, got {self.signal}")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if self.entry is not None and self.entry <= 0:
            raise ValueError(f"entry price must be positive, got {self.entry}")
            
        if self.stop is not None and self.stop <= 0:
            raise ValueError(f"stop price must be positive, got {self.stop}")


class Strategy(Protocol):
    """
    Protocol defining the interface that all trading strategies must implement.
    
    This protocol ensures consistent behavior across all strategy implementations
    while allowing for flexible strategy-specific logic and parameters.
    """
    
    def compute(self, df: pd.DataFrame, **params) -> StrategyResult:
        """
        Compute trading signal from OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            **params: Strategy-specific parameters
            
        Returns:
            StrategyResult containing signal, entry/stop levels, confidence, and metadata
            
        Raises:
            ValueError: If required data columns are missing or invalid parameters provided
        """
        ...
    
    @property
    def requires_volume(self) -> bool:
        """
        Whether this strategy requires volume data to function properly.
        
        Returns:
            True if strategy needs volume column, False if it can work with price data only
        """
        ...
    
    @property
    def default_params(self) -> Dict[str, Any]:
        """
        Default parameter values for this strategy.
        
        Returns:
            Dictionary of parameter names to default values
        """
        ...
    
    @property
    def param_schema(self) -> Dict[str, Any]:
        """
        JSON schema describing valid parameters for this strategy.
        
        Returns:
            JSON schema object with parameter validation rules
        """
        ...


class StrategyError(Exception):
    """Base exception for strategy-related errors."""
    pass


class StrategyNotFoundError(StrategyError):
    """Raised when a requested strategy ID is not found in the registry."""
    pass


class ParameterValidationError(StrategyError):
    """Raised when strategy parameters fail validation against the schema."""
    pass