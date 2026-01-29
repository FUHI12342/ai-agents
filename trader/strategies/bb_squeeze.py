"""
Bollinger Band Squeeze Strategy

This strategy identifies periods of low volatility (squeeze) followed by volatility expansion.
The strategy looks for Bollinger Band contractions and generates signals when the bands
start to expand, indicating potential breakout opportunities.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base import Strategy, StrategyResult


class BBSqueezeStrategy:
    """
    Bollinger Band Squeeze Strategy implementation.
    
    The strategy works by:
    1. Calculating Bollinger Bands (typically 20-period with 2 std dev)
    2. Measuring band width as a proxy for volatility
    3. Identifying squeeze periods (low volatility)
    4. Generating signals when volatility starts expanding after a squeeze
    """
    
    @property
    def requires_volume(self) -> bool:
        """BB Squeeze strategy works with price data only."""
        return False
    
    @property
    def default_params(self) -> Dict[str, Any]:
        """Default parameters for BB Squeeze strategy."""
        return {
            "bb_period": 20,
            "bb_std": 2.0,
            "squeeze_threshold": 0.1,
            "atr_period": 14
        }
    
    @property
    def param_schema(self) -> Dict[str, Any]:
        """JSON schema for BB Squeeze parameters."""
        return {
            "type": "object",
            "properties": {
                "bb_period": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 5,
                    "maximum": 100,
                    "description": "Bollinger Band period"
                },
                "bb_std": {
                    "type": "number",
                    "default": 2.0,
                    "minimum": 0.5,
                    "maximum": 4.0,
                    "description": "Bollinger Band standard deviation multiplier"
                },
                "squeeze_threshold": {
                    "type": "number",
                    "default": 0.1,
                    "minimum": 0.01,
                    "maximum": 1.0,
                    "description": "Threshold for identifying squeeze conditions"
                },
                "atr_period": {
                    "type": "integer",
                    "default": 14,
                    "minimum": 5,
                    "maximum": 50,
                    "description": "Average True Range period for volatility measurement"
                }
            },
            "required": ["bb_period", "bb_std", "squeeze_threshold"]
        }
    
    def compute(self, df: pd.DataFrame, **params) -> StrategyResult:
        """
        Compute BB Squeeze signal from OHLCV DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
            **params: Strategy parameters
            
        Returns:
            StrategyResult with signal, entry/stop levels, and metadata
        """
        # Get parameters with defaults
        bb_period = params.get("bb_period", self.default_params["bb_period"])
        bb_std = params.get("bb_std", self.default_params["bb_std"])
        squeeze_threshold = params.get("squeeze_threshold", self.default_params["squeeze_threshold"])
        atr_period = params.get("atr_period", self.default_params["atr_period"])
        
        # Validate we have required columns
        close_col = self._get_close_column(df)
        high_col = self._get_high_column(df)
        low_col = self._get_low_column(df)
        
        if not all([close_col, high_col, low_col]):
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "Missing required OHLC columns",
                    "reasons": ["missing_data"]
                }
            )
        
        # Check if we have enough data
        min_data_needed = max(bb_period, atr_period) + 10  # Extra buffer for calculations
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
        
        # Calculate Bollinger Bands
        df_work['bb_middle'] = df_work[close_col].rolling(window=bb_period).mean()
        bb_std_dev = df_work[close_col].rolling(window=bb_period).std()
        df_work['bb_upper'] = df_work['bb_middle'] + (bb_std_dev * bb_std)
        df_work['bb_lower'] = df_work['bb_middle'] - (bb_std_dev * bb_std)
        
        # Calculate band width (normalized by middle band)
        df_work['bb_width'] = (df_work['bb_upper'] - df_work['bb_lower']) / df_work['bb_middle']
        
        # Calculate ATR for volatility measurement
        df_work['tr'] = np.maximum(
            df_work[high_col] - df_work[low_col],
            np.maximum(
                abs(df_work[high_col] - df_work[close_col].shift(1)),
                abs(df_work[low_col] - df_work[close_col].shift(1))
            )
        )
        df_work['atr'] = df_work['tr'].rolling(window=atr_period).mean()
        
        # Identify squeeze conditions
        df_work['bb_width_ma'] = df_work['bb_width'].rolling(window=bb_period).mean()
        df_work['is_squeeze'] = df_work['bb_width'] < (df_work['bb_width_ma'] * (1 - squeeze_threshold))
        
        # Get recent data for signal generation
        recent_data = df_work.tail(5)
        
        if len(recent_data) < 3:
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
        current_bb_upper = recent_data['bb_upper'].iloc[-1]
        current_bb_lower = recent_data['bb_lower'].iloc[-1]
        current_bb_middle = recent_data['bb_middle'].iloc[-1]
        current_bb_width = recent_data['bb_width'].iloc[-1]
        current_atr = recent_data['atr'].iloc[-1]
        
        # Check for valid values
        if pd.isna(current_bb_width) or pd.isna(current_atr):
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
        
        # Check if we're coming out of a squeeze
        was_in_squeeze = recent_data['is_squeeze'].iloc[-3:-1].any()  # Previous 2 bars
        is_currently_squeeze = recent_data['is_squeeze'].iloc[-1]
        
        # Volatility expansion signal
        if was_in_squeeze and not is_currently_squeeze:
            # Determine direction based on price position relative to BB middle
            if current_close > current_bb_middle:
                # Bullish breakout
                confidence = min((current_close - current_bb_middle) / (current_bb_upper - current_bb_middle), 1.0)
                entry_price = current_close
                stop_price = max(current_bb_lower, current_close - (current_atr * 2))
                
                return StrategyResult(
                    signal=1,
                    entry=entry_price,
                    stop=stop_price,
                    confidence=confidence,
                    meta={
                        "reasons": ["bb_squeeze_breakout_bullish"],
                        "bb_width": current_bb_width,
                        "bb_upper": current_bb_upper,
                        "bb_lower": current_bb_lower,
                        "bb_middle": current_bb_middle,
                        "atr": current_atr,
                        "was_in_squeeze": was_in_squeeze
                    }
                )
            else:
                # Bearish breakout
                confidence = min((current_bb_middle - current_close) / (current_bb_middle - current_bb_lower), 1.0)
                entry_price = current_close
                stop_price = min(current_bb_upper, current_close + (current_atr * 2))
                
                return StrategyResult(
                    signal=-1,
                    entry=entry_price,
                    stop=stop_price,
                    confidence=confidence,
                    meta={
                        "reasons": ["bb_squeeze_breakout_bearish"],
                        "bb_width": current_bb_width,
                        "bb_upper": current_bb_upper,
                        "bb_lower": current_bb_lower,
                        "bb_middle": current_bb_middle,
                        "atr": current_atr,
                        "was_in_squeeze": was_in_squeeze
                    }
                )
        
        # No signal
        return StrategyResult(
            signal=0,
            entry=None,
            stop=None,
            confidence=0.0,
            meta={
                "reasons": ["no_signal"],
                "bb_width": current_bb_width,
                "bb_upper": current_bb_upper,
                "bb_lower": current_bb_lower,
                "bb_middle": current_bb_middle,
                "atr": current_atr,
                "is_squeeze": is_currently_squeeze,
                "was_in_squeeze": was_in_squeeze
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