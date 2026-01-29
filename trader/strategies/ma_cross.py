"""
Moving Average Crossover Strategy

This strategy implements a classic moving average crossover system where
buy signals are generated when a short-period MA crosses above a long-period MA,
and sell signals when the short MA crosses below the long MA.
"""

from typing import Optional, Sequence, Tuple, Dict, Any
import pandas as pd
import numpy as np

from .base import Strategy, StrategyResult
from ..paper_engine import OHLCV


class MACrossStrategy:
    """Moving Average Crossover Strategy implementation."""
    
    @property
    def requires_volume(self) -> bool:
        """MA Cross strategy doesn't require volume data."""
        return False
    
    @property
    def default_params(self) -> Dict[str, Any]:
        """Default parameters for MA Cross strategy."""
        return {
            "ma_short": 20,
            "ma_long": 100
        }
    
    @property
    def param_schema(self) -> Dict[str, Any]:
        """JSON schema for MA Cross parameters."""
        return {
            "type": "object",
            "properties": {
                "ma_short": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Short moving average period"
                },
                "ma_long": {
                    "type": "integer", 
                    "default": 100,
                    "minimum": 2,
                    "maximum": 500,
                    "description": "Long moving average period"
                }
            },
            "required": ["ma_short", "ma_long"]
        }
    
    def compute(self, df: pd.DataFrame, **params) -> StrategyResult:
        """
        Compute MA cross signal from OHLCV DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
            **params: Strategy parameters (ma_short, ma_long)
            
        Returns:
            StrategyResult with signal, confidence, and metadata
        """
        # Get parameters with defaults
        ma_short = params.get("ma_short", self.default_params["ma_short"])
        ma_long = params.get("ma_long", self.default_params["ma_long"])
        
        # Validate parameters
        if ma_short <= 0 or ma_long <= 0 or ma_short >= ma_long:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": f"Invalid MA parameters: ma_short={ma_short}, ma_long={ma_long}",
                    "reasons": ["parameter_error"]
                }
            )
        
        # Check if we have enough data
        if len(df) < ma_long:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": f"Insufficient data: need {ma_long} bars, got {len(df)}",
                    "reasons": ["insufficient_data"]
                }
            )
        
        # Calculate moving averages
        close_col = self._get_close_column(df)
        if close_col is None:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "No close price column found",
                    "reasons": ["missing_data"]
                }
            )
        
        df_work = df.copy()
        df_work[f'ma_{ma_short}'] = df_work[close_col].rolling(window=ma_short).mean()
        df_work[f'ma_{ma_long}'] = df_work[close_col].rolling(window=ma_long).mean()
        
        # Get the last few rows to detect crossover
        recent_data = df_work.tail(3)  # Current + 2 previous bars
        
        if len(recent_data) < 2:
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "Not enough recent data for crossover detection",
                    "reasons": ["insufficient_recent_data"]
                }
            )
        
        # Get current and previous MA values
        current_short = recent_data[f'ma_{ma_short}'].iloc[-1]
        current_long = recent_data[f'ma_{ma_long}'].iloc[-1]
        prev_short = recent_data[f'ma_{ma_short}'].iloc[-2]
        prev_long = recent_data[f'ma_{ma_long}'].iloc[-2]
        
        # Check for valid MA values
        if pd.isna(current_short) or pd.isna(current_long) or pd.isna(prev_short) or pd.isna(prev_long):
            return StrategyResult(
                signal=0,
                entry=None,
                stop=None,
                confidence=0.0,
                meta={
                    "error": "MA values contain NaN",
                    "reasons": ["invalid_ma_values"]
                }
            )
        
        # Detect crossover
        current_diff = current_short - current_long
        prev_diff = prev_short - prev_long
        
        # Current price for entry/stop calculation
        current_price = df_work[close_col].iloc[-1]
        
        # Bullish crossover (short MA crosses above long MA)
        if prev_diff <= 0 and current_diff > 0:
            confidence = min(abs(current_diff) / current_long, 1.0)  # Normalize confidence
            return StrategyResult(
                signal=1,
                entry=current_price,
                stop=current_price * 0.95,  # 5% stop loss
                confidence=confidence,
                meta={
                    "reasons": ["ma_cross_up"],
                    "ma_short": current_short,
                    "ma_long": current_long,
                    "ma_diff": current_diff,
                    "prev_diff": prev_diff
                }
            )
        
        # Bearish crossover (short MA crosses below long MA)
        elif prev_diff >= 0 and current_diff < 0:
            confidence = min(abs(current_diff) / current_long, 1.0)
            return StrategyResult(
                signal=-1,
                entry=current_price,
                stop=current_price * 1.05,  # 5% stop loss for short
                confidence=confidence,
                meta={
                    "reasons": ["ma_cross_down"],
                    "ma_short": current_short,
                    "ma_long": current_long,
                    "ma_diff": current_diff,
                    "prev_diff": prev_diff
                }
            )
        
        # No crossover
        return StrategyResult(
            signal=0,
            entry=None,
            stop=None,
            confidence=0.0,
            meta={
                "reasons": ["no_signal"],
                "ma_short": current_short,
                "ma_long": current_long,
                "ma_diff": current_diff
            }
        )
    
    def _get_close_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the close price column in the DataFrame."""
        close_candidates = ['close', 'Close', 'CLOSE', 'c', 'C']
        for col in close_candidates:
            if col in df.columns:
                return col
        return None


# Legacy function for backward compatibility
def calculate_ma_cross_signal(
    ohlcv: Sequence[OHLCV],
    ma_short: int,
    ma_long: int,
    prev_diff: Optional[float] = None,
) -> Tuple[int, str, Optional[float]]:
    """
    Legacy MA cross signal calculation for backward compatibility.
    
    This function maintains the original interface while using the new strategy internally.
    
    Returns: (target_position, reason, updated_prev_diff)
    target_position: 0 (no position) or 1 (full position)
    """
    if ma_short <= 0 or ma_long <= 0 or ma_short >= ma_long:
        raise ValueError("ma_short must be >0 and < ma_long")

    # Use original rolling calculation for exact backward compatibility
    if not ohlcv:
        return -1, "no_signal", prev_diff
    
    # Rolling sums for SMA
    short_sum = 0.0
    long_sum = 0.0
    short_q = []
    long_q = []

    # Process candles
    for (ts, o, h, l, c, v) in ohlcv:
        close = float(c)

        # Update rolling windows
        short_q.append(close)
        short_sum += close
        if len(short_q) > ma_short:
            short_sum -= short_q.pop(0)

        long_q.append(close)
        long_sum += close
        if len(long_q) > ma_long:
            long_sum -= long_q.pop(0)

        # Check if MA ready
        short_ma = short_sum / ma_short if len(short_q) == ma_short else None
        long_ma = long_sum / ma_long if len(long_q) == ma_long else None

        if short_ma is None or long_ma is None:
            continue

        diff = float(short_ma - long_ma)

        # Initialize prev_diff
        if prev_diff is None:
            prev_diff = diff
            continue

        # Detect cross
        crossed_up = (prev_diff <= 0.0 and diff > 0.0)
        crossed_down = (prev_diff >= 0.0 and diff < 0.0)

        if crossed_up:
            return 1, "ma_cross_up", diff
        elif crossed_down:
            return 0, "ma_cross_down", diff

        # Update prev_diff
        prev_diff = diff

    # No signal
    return -1, "no_signal", prev_diff