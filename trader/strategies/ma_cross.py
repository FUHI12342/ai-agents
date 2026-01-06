from typing import Optional, Sequence, Tuple
from ..paper_engine import OHLCV

def calculate_ma_cross_signal(
    ohlcv: Sequence[OHLCV],
    ma_short: int,
    ma_long: int,
    prev_diff: Optional[float] = None,
) -> Tuple[int, str, Optional[float]]:
    """
    Calculate MA cross signal for long-only strategy.
    Returns: (target_position, reason, updated_prev_diff)
    target_position: 0 (no position) or 1 (full position)
    """
    if ma_short <= 0 or ma_long <= 0 or ma_short >= ma_long:
        raise ValueError("ma_short must be >0 and < ma_long")

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