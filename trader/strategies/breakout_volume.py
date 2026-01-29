"""
Breakout Volume Strategy

This strategy identifies range breakouts confirmed by above-average volume.
It looks for price breaking out of recent trading ranges with volume confirmation
to filter out false breakouts.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base import Strategy, StrategyResult


class BreakoutVolumeStrategy:
    """
    Breakout Volume Strategy implementation.
    
    The strategy works by:
    1. Identifying recent price ranges (support/resistance levels)
    2. Detecting breakouts above/below these ranges
    3. Confirming breakouts with above-average volume
    4. Generating signals only when both price and volume conditions are met
    """
    
    @property
    def requires_volume(self) -> bool:
        """Breakout Volume strategy requires volume data for confirmation."""
        return True
    
    @property
    def default_params(self) -> Dict[str, Any]:
        """Default parameters for Breakout Volume strategy."""
        return {
            "lookback_period": 20,
            "volume_threshold": 1.5,
            "breakout_threshold": 0.02,
            "atr_period": 14
        }
    
    @property
    def param_schema(self) -> Dict[str, Any]:
        """JSON schema for Breakout Volume parameters."""
        return {
            "type": "object",
            "properties": {
                "lookback_period": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 5,
                    "maximum": 100,
                    "description": "Period for identifying support/resistance levels"
                },
                "volume_threshold": {
                    "type": "number",
                    "default": 1.5,
                    "minimum": 1.0,
                    "maximum": 5.0,
                    "description": "Volume multiplier for confirmation (1.5 = 50% above average)"
                },
                "breakout_threshold": {
                    "type": "number",
                    "default": 0.02,
                    "minimum": 0.005,
                    "maximum": 0.1,
                    "description": "Minimum breakout percentage to trigger signal"
                },
                "atr_period": {
                    "type": "integer",
                    "default": 14,
                    "minimum": 5,
                    "maximum": 50,
                    "description": "Average True Range period for stop loss calculation"
                }
            },
            "required": ["lookback_period", "volume_threshold"]
        }
    
    def compute(self, df: pd.DataFrame, **params) -> StrategyResult:
        """
        Compute Breakout Volume signal from OHLCV DataFrame.
        
        Args:
            df: DataFrame with OHLCV data including volume
            **params: Strategy parameters
            
        Returns:
            StrategyResult with signal, entry/stop levels, and metadata
        """
        # Get parameters with defaults
        lookback_period = params.get("lookback_period", self.default_params["lookback_period"])
        volume_threshold = params.get("volume_threshold", self.default_params["volume_threshold"])
        breakout_threshold = params.get("breakout_threshold", self.default_params["breakout_threshold"])
        atr_period = params.get("atr_period", self.default_params["atr_period"])
        
        # Validate we have required columns
        close_col = self._get_close_column(df)
        high_col = self._get_high_column(df)
        low_col = self._get_low_column(df)
        volume_col = self._get_volume_column(df)
        
        if not all([close_col, high_col, low_col, volume_col]):
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "Missing required OHLCV columns",
                    "reasons": ["missing_data"]
                }
            )
        
        # Check if we have enough data
        min_data_needed = max(lookback_period, atr_period) + 5
        if len(df) < min_data_needed:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": f"Insufficient data: need {min_data_needed} bars, got {len(df)}",
                    "reasons": ["insufficient_data"]
                }
            )
        
        df_work = df.copy()
        
        # Calculate rolling support and resistance levels
        df_work['resistance'] = df_work[high_col].rolling(window=lookback_period).max()
        df_work['support'] = df_work[low_col].rolling(window=lookback_period).min()
        df_work['range_size'] = df_work['resistance'] - df_work['support']
        
        # Calculate volume moving average
        df_work['volume_ma'] = df_work[volume_col].rolling(window=lookback_period).mean()
        df_work['volume_ratio'] = df_work[volume_col] / df_work['volume_ma']
        
        # Calculate ATR for stop loss
        df_work['tr'] = np.maximum(
            df_work[high_col] - df_work[low_col],
            np.maximum(
                abs(df_work[high_col] - df_work[close_col].shift(1)),
                abs(df_work[low_col] - df_work[close_col].shift(1))
            )
        )
        df_work['atr'] = df_work['tr'].rolling(window=atr_period).mean()
        
        # Get recent data
        recent_data = df_work.tail(3)
        
        if len(recent_data) < 2:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "Not enough recent data",
                    "reasons": ["insufficient_recent_data"]
                }
            )
        
        # Current values
        current_close = recent_data[close_col].iloc[-1]
        current_high = recent_data[high_col].iloc[-1]
        current_low = recent_data[low_col].iloc[-1]
        current_volume = recent_data[volume_col].iloc[-1]
        current_resistance = recent_data['resistance'].iloc[-1]
        current_support = recent_data['support'].iloc[-1]
        current_volume_ratio = recent_data['volume_ratio'].iloc[-1]
        current_atr = recent_data['atr'].iloc[-1]
        
        # Previous values for comparison
        prev_close = recent_data[close_col].iloc[-2]
        prev_high = recent_data[high_col].iloc[-2]
        prev_low = recent_data[low_col].iloc[-2]
        
        # Check for valid values
        if any(pd.isna(val) for val in [current_resistance, current_support, current_volume_ratio, current_atr]):
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "Invalid indicator values",
                    "reasons": ["invalid_indicators"]
                }
            )
        
        # Check for volume confirmation
        volume_confirmed = current_volume_ratio >= volume_threshold
        
        # Calculate breakout thresholds
        resistance_breakout_level = current_resistance * (1 + breakout_threshold)
        support_breakout_level = current_support * (1 - breakout_threshold)
        
        # Bullish breakout detection
        if (current_high > resistance_breakout_level and 
            prev_high <= current_resistance and 
            volume_confirmed):
            
            # Calculate confidence based on breakout strength and volume
            breakout_strength = (current_high - current_resistance) / current_resistance
            volume_strength = min((current_volume_ratio - 1.0) / 2.0, 1.0)  # Normalize volume strength
            confidence = min((breakout_strength * 10 + volume_strength) / 2, 1.0)
            
            entry_price = current_close
            stop_price = max(current_support, current_close - (current_atr * 2))
            
            return StrategyResult(
                signal=1,
                entry=entry_price,
                stop=stop_price,
                confidence=confidence,
                meta={
                    "reasons": ["resistance_breakout_with_volume"],
                    "resistance": current_resistance,
                    "support": current_support,
                    "volume_ratio": current_volume_ratio,
                    "breakout_strength": breakout_strength,
                    "volume_threshold": volume_threshold,
                    "atr": current_atr
                }
            )
        
        # Bearish breakout detection
        elif (current_low < support_breakout_level and 
              prev_low >= current_support and 
              volume_confirmed):
            
            # Calculate confidence based on breakout strength and volume
            breakout_strength = (current_support - current_low) / current_support
            volume_strength = min((current_volume_ratio - 1.0) / 2.0, 1.0)
            confidence = min((breakout_strength * 10 + volume_strength) / 2, 1.0)
            
            entry_price = current_close
            stop_price = min(current_resistance, current_close + (current_atr * 2))
            
            return StrategyResult(
                signal=-1,
                entry=entry_price,
                stop=stop_price,
                confidence=confidence,
                meta={
                    "reasons": ["support_breakout_with_volume"],
                    "resistance": current_resistance,
                    "support": current_support,
                    "volume_ratio": current_volume_ratio,
                    "breakout_strength": breakout_strength,
                    "volume_threshold": volume_threshold,
                    "atr": current_atr
                }
            )
        
        # No signal - check why
        reasons = ["no_signal"]
        if not volume_confirmed:
            reasons.append("insufficient_volume")
        if current_high <= resistance_breakout_level and current_low >= support_breakout_level:
            reasons.append("no_breakout")
        
        return StrategyResult(
            signal=0,
            entry=None,
            stop=None,
            confidence=0.0,
            meta={
                "reasons": reasons,
                "resistance": current_resistance,
                "support": current_support,
                "volume_ratio": current_volume_ratio,
                "volume_threshold": volume_threshold,
                "resistance_breakout_level": resistance_breakout_level,
                "support_breakout_level": support_breakout_level,
                "volume_confirmed": volume_confirmed
            }
        )
    
    def _get_close_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the close price column in the DataFrame."""
        close_candidates = ['close', 'Close', 'CLOSE', 'c', 'C']
        for col in close_candidates:
            if col in df.columns:
                return col
        return None
    
    def _get_high_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the high price column in the DataFrame."""
        high_candidates = ['high', 'High', 'HIGH', 'h', 'H']
        for col in high_candidates:
            if col in df.columns:
                return col
        return None
    
    def _get_low_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the low price column in the DataFrame."""
        low_candidates = ['low', 'Low', 'LOW', 'l', 'L']
        for col in low_candidates:
            if col in df.columns:
                return col
        return None
    
    def _get_volume_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the volume column in the DataFrame."""
        volume_candidates = ['volume', 'Volume', 'VOLUME', 'vol', 'Vol', 'VOL', 'v', 'V']
        for col in volume_candidates:
            if col in df.columns:
                return col
        return None