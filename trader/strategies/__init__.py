"""
Strategies package

This package provides the strategy plugin system for the trading platform.
It includes the registry for strategy management and implementations of
various trading strategies.
"""

from .registry import registry
from .base import Strategy, StrategyResult, StrategyError, StrategyNotFoundError, ParameterValidationError
from .ma_cross import MACrossStrategy
from .bb_squeeze import BBSqueezeStrategy
from .breakout_volume import BreakoutVolumeStrategy

# Register all available strategies
registry.register(
    "ma_cross",
    MACrossStrategy,
    "Moving Average Crossover",
    "Classic MA crossover strategy with configurable periods",
    recommended=False  # Legacy strategy, not recommended as default
)

registry.register(
    "bb_squeeze",
    BBSqueezeStrategy,
    "Bollinger Band Squeeze",
    "Volatility expansion strategy based on Bollinger Band squeeze patterns",
    recommended=True  # Default recommended strategy
)

registry.register(
    "breakout_volume",
    BreakoutVolumeStrategy,
    "Volume Breakout",
    "Range breakout strategy with volume confirmation",
    recommended=True
)

# Export the registry and key classes
__all__ = [
    'registry',
    'Strategy',
    'StrategyResult',
    'StrategyError',
    'StrategyNotFoundError',
    'ParameterValidationError',
    'MACrossStrategy',
    'BBSqueezeStrategy',
    'BreakoutVolumeStrategy'
]