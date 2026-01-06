from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# OHLCV: (ts_ms, open, high, low, close, volume)
OHLCV = Tuple[int, float, float, float, float, float]


@dataclass
class PaperState:
    cash_quote: float                      # e.g. USDT cash
    pos_base: float                        # e.g. BTC position size
    last_ts: Optional[int] = None          # last processed candle ts (ms)
    prev_diff: Optional[float] = None      # previous (ma_short - ma_long)
    peak_equity_quote: Optional[float] = None
    max_drawdown_pct: float = 0.0
    trades_total: int = 0


def _slip_factor(slippage_bps: float) -> float:
    return float(slippage_bps) / 10000.0


def simulate_ma_cross(
    ohlcv: Sequence[OHLCV],
    state: PaperState,
    *,
    ma_short: int,
    ma_long: int,
    risk_pct: float,
    fee_rate: float,
    slippage_bps: float,
    symbol: str,
) -> Tuple[PaperState, List[Dict[str, Any]], List[Tuple[int, float]]]:
    """
    Long-only MA cross paper simulation.
    BUY when short crosses above long; SELL when crosses below long (close all).
    Execution price includes slippage; fee charged on notional.

    Returns: (updated_state, new_trades, equity_curve_ts_quote)
    """
    if ma_short <= 0 or ma_long <= 0 or ma_short >= ma_long:
        raise ValueError("ma_short must be >0 and < ma_long")

    risk_pct = max(0.0, min(float(risk_pct), 1.0))
    fee_rate = max(0.0, float(fee_rate))
    slip = _slip_factor(slippage_bps)

    # rolling sums for SMA
    short_sum = 0.0
    long_sum = 0.0
    short_q: List[float] = []
    long_q: List[float] = []

    new_trades: List[Dict[str, Any]] = []
    equity_curve: List[Tuple[int, float]] = []

    def mark_equity(close_price: float) -> float:
        return state.cash_quote + state.pos_base * close_price

    for (ts, o, h, l, c, v) in ohlcv:
        close = float(c)

        # update rolling windows
        short_q.append(close)
        short_sum += close
        if len(short_q) > ma_short:
            short_sum -= short_q.pop(0)

        long_q.append(close)
        long_sum += close
        if len(long_q) > ma_long:
            long_sum -= long_q.pop(0)

        short_ma = (short_sum / ma_short) if len(short_q) == ma_short else None
        long_ma = (long_sum / ma_long) if len(long_q) == ma_long else None

        # always advance "last_ts" boundary logic AFTER MA ready calc
        if state.last_ts is not None and ts <= state.last_ts:
            continue

        # if MA not ready, just update last_ts and continue
        if short_ma is None or long_ma is None:
            state.last_ts = ts
            continue

        diff = float(short_ma - long_ma)

        # init prev_diff if needed
        if state.prev_diff is None:
            state.prev_diff = diff
            state.last_ts = ts

            eq = mark_equity(close)
            equity_curve.append((ts, eq))
            if state.peak_equity_quote is None or eq > state.peak_equity_quote:
                state.peak_equity_quote = eq
            continue

        # detect cross
        crossed_up = (state.prev_diff <= 0.0 and diff > 0.0)
        crossed_down = (state.prev_diff >= 0.0 and diff < 0.0)

        reason = ""
        if crossed_up and state.cash_quote > 0.0 and risk_pct > 0.0:
            # BUY: allocate risk_pct of current cash
            invest = state.cash_quote * risk_pct
            exec_price = close * (1.0 + slip)
            qty = invest / exec_price if exec_price > 0 else 0.0
            notional = qty * exec_price
            fee = notional * fee_rate

            # apply
            state.cash_quote -= (notional + fee)
            state.pos_base += qty
            state.trades_total += 1
            reason = "ma_cross_up_buy"

            new_trades.append({
                "time_ms": ts,
                "symbol": symbol,
                "side": "BUY",
                "price": exec_price,
                "qty": qty,
                "notional_quote": notional,
                "fee_quote": fee,
                "cash_quote_after": state.cash_quote,
                "pos_base_after": state.pos_base,
                "reason": reason,
            })

        elif crossed_down and state.pos_base > 0.0:
            # SELL: close all
            qty = state.pos_base
            exec_price = close * (1.0 - slip)
            notional = qty * exec_price
            fee = notional * fee_rate

            state.pos_base = 0.0
            state.cash_quote += (notional - fee)
            state.trades_total += 1
            reason = "ma_cross_down_sell"

            new_trades.append({
                "time_ms": ts,
                "symbol": symbol,
                "side": "SELL",
                "price": exec_price,
                "qty": qty,
                "notional_quote": notional,
                "fee_quote": fee,
                "cash_quote_after": state.cash_quote,
                "pos_base_after": state.pos_base,
                "reason": reason,
            })

        # update equity / drawdown
        eq = mark_equity(close)
        equity_curve.append((ts, eq))

        if state.peak_equity_quote is None or eq > state.peak_equity_quote:
            state.peak_equity_quote = eq

        if state.peak_equity_quote and state.peak_equity_quote > 0:
            dd = (eq / state.peak_equity_quote - 1.0) * 100.0  # negative when drawdown
            if dd < state.max_drawdown_pct:
                state.max_drawdown_pct = dd

        state.prev_diff = diff
        state.last_ts = ts

    return state, new_trades, equity_curve