"""
Strategy Registry for managing trading strategy plugins.

This module provides the central registry for strategy discovery, instantiation,
and fallback logic. It handles volume dependency resolution and automatic
strategy downgrades when required data is unavailable.
"""

from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
import pandas as pd
import logging

from .base import Strategy, StrategyResult, StrategyNotFoundError, ParameterValidationError

logger = logging.getLogger(__name__)


@dataclass
class StrategyInfo:
    """
    Metadata information about a registered strategy.
    
    Attributes:
        id: Unique strategy identifier
        name: Human-readable strategy name
        description: Strategy description
        recommended: Whether this strategy is recommended for general use
        requires_volume: Whether strategy needs volume data
        param_schema: JSON schema for parameter validation
    """
    id: str
    name: str
    description: str
    recommended: bool
    requires_volume: bool
    param_schema: Dict[str, Any]


class StrategyRegistry:
    """
    Central registry for managing trading strategy plugins.
    
    The registry provides strategy discovery, instantiation, and automatic
    fallback logic for volume-dependent strategies.
    """
    
    def __init__(self):
        """Initialize empty strategy registry."""
        self._strategies: Dict[str, Type[Strategy]] = {}
        self._strategy_info: Dict[str, StrategyInfo] = {}
        self._default_strategy_id = "bb_squeeze"
    
    def register(self, strategy_id: str, strategy_class: Type[Strategy], 
                 name: str, description: str, recommended: bool = False) -> None:
        """
        Register a strategy class with the registry.
        
        Args:
            strategy_id: Unique identifier for the strategy
            strategy_class: Strategy class implementing the Strategy protocol
            name: Human-readable name
            description: Strategy description
            recommended: Whether this is a recommended strategy
        """
        if strategy_id in self._strategies:
            logger.warning(f"Strategy '{strategy_id}' already registered, overwriting")
        
        # Create instance to get metadata
        instance = strategy_class()
        
        self._strategies[strategy_id] = strategy_class
        self._strategy_info[strategy_id] = StrategyInfo(
            id=strategy_id,
            name=name,
            description=description,
            recommended=recommended,
            requires_volume=instance.requires_volume,
            param_schema=instance.param_schema
        )
        
        logger.debug(f"Registered strategy: {strategy_id} ({name})")
    
    def get_strategy(self, strategy_id: str) -> Strategy:
        """
        Get strategy instance by ID.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy instance
            
        Raises:
            StrategyNotFoundError: If strategy ID is not found
        """
        if strategy_id not in self._strategies:
            available = list(self._strategies.keys())
            raise StrategyNotFoundError(
                f"Strategy '{strategy_id}' not found. Available strategies: {available}"
            )
        
        strategy_class = self._strategies[strategy_id]
        return strategy_class()
    
    def list_strategies(self) -> List[StrategyInfo]:
        """
        List all available strategies with metadata.
        
        Returns:
            List of StrategyInfo objects containing strategy metadata
        """
        return list(self._strategy_info.values())
    
    def resolve_strategy(self, strategy_id: Optional[str], df: pd.DataFrame) -> Strategy:
        """
        Resolve strategy with volume fallback logic.
        
        This method handles automatic fallback for volume-dependent strategies
        when volume data is not available in the DataFrame.
        
        Args:
            strategy_id: Requested strategy ID (None for default)
            df: DataFrame to check for volume data availability
            
        Returns:
            Strategy instance (may be fallback strategy)
        """
        original_strategy_id = strategy_id
        
        # Use default if no strategy specified
        if strategy_id is None:
            strategy_id = self._default_strategy_id
            logger.info(f"No strategy specified, using default: {strategy_id}")
        
        # Check if requested strategy exists
        if strategy_id not in self._strategies:
            logger.warning(f"Strategy '{strategy_id}' not found, falling back to default: {self._default_strategy_id}")
            strategy_id = self._default_strategy_id
        
        # Get strategy info
        strategy_info = self._strategy_info[strategy_id]
        
        # Check volume requirement and implement fallback logic
        if strategy_info.requires_volume:
            has_volume = self._check_volume_data(df)
            if not has_volume:
                # Fallback to bb_squeeze (volume-independent strategy)
                fallback_id = "bb_squeeze"
                logger.warning(
                    f"Strategy '{strategy_id}' requires volume data but none found. "
                    f"Falling back to '{fallback_id}'"
                )
                
                # Add fallback information to the strategy instance
                strategy = self.get_strategy(fallback_id)
                # Store fallback info for later use in signal output
                if hasattr(strategy, '_fallback_info'):
                    strategy._fallback_info = {
                        'original_strategy': original_strategy_id or strategy_id,
                        'fallback_strategy': fallback_id,
                        'fallback_reason': 'missing_volume_data'
                    }
                
                return strategy
        
        return self.get_strategy(strategy_id)
    
    def _check_volume_data(self, df: pd.DataFrame) -> bool:
        """
        Check if DataFrame contains usable volume data.
        
        Args:
            df: DataFrame to check
            
        Returns:
            True if volume data is available and usable
        """
        if df.empty:
            return False
        
        # Check for volume column (case insensitive)
        volume_cols = [col for col in df.columns if col.lower() in ['volume', 'vol', 'v']]
        if not volume_cols:
            return False
        
        volume_col = volume_cols[0]
        
        # Check if volume data is not all zeros/nulls
        volume_series = df[volume_col]
        if volume_series.isna().all():
            return False
        
        # Check if we have meaningful volume data (not all zeros)
        non_zero_volume = volume_series[volume_series > 0]
        return len(non_zero_volume) > 0
    
    def validate_params(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate strategy parameters against schema.
        
        Args:
            strategy_id: Strategy identifier
            params: Parameters to validate
            
        Returns:
            Validated parameters with defaults applied
            
        Raises:
            StrategyNotFoundError: If strategy not found
            ParameterValidationError: If parameters are invalid
        """
        if strategy_id not in self._strategy_info:
            raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found")
        
        strategy_info = self._strategy_info[strategy_id]
        schema = strategy_info.param_schema
        
        # Get strategy instance for default params
        strategy = self.get_strategy(strategy_id)
        defaults = strategy.default_params
        
        # Apply defaults for missing parameters
        validated_params = defaults.copy()
        validated_params.update(params)
        
        # Basic validation against schema
        if "properties" in schema:
            for param_name, param_schema in schema["properties"].items():
                if param_name in validated_params:
                    value = validated_params[param_name]
                    param_type = param_schema.get("type")
                    
                    # Type validation
                    if param_type == "integer" and not isinstance(value, int):
                        try:
                            validated_params[param_name] = int(value)
                        except (ValueError, TypeError):
                            raise ParameterValidationError(
                                f"Parameter '{param_name}' must be an integer, got {type(value).__name__}"
                            )
                    
                    elif param_type == "number" and not isinstance(value, (int, float)):
                        try:
                            validated_params[param_name] = float(value)
                        except (ValueError, TypeError):
                            raise ParameterValidationError(
                                f"Parameter '{param_name}' must be a number, got {type(value).__name__}"
                            )
                    
                    # Range validation
                    if "minimum" in param_schema:
                        if validated_params[param_name] < param_schema["minimum"]:
                            raise ParameterValidationError(
                                f"Parameter '{param_name}' must be >= {param_schema['minimum']}, got {validated_params[param_name]}"
                            )
                    
                    if "maximum" in param_schema:
                        if validated_params[param_name] > param_schema["maximum"]:
                            raise ParameterValidationError(
                                f"Parameter '{param_name}' must be <= {param_schema['maximum']}, got {validated_params[param_name]}"
                            )
        
        return validated_params


# Global registry instance
registry = StrategyRegistry()