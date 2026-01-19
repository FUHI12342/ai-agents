from typing import Optional, Tuple
from .config import TraderConfig
from .ledger import Ledger
from .brokers.base import Broker

def check_risk_limits(
    config: TraderConfig,
    ledger: Ledger,
    broker: Broker,
    action: Optional[str],
    symbol: str,
    amount: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Check risk limits before trading.
    Returns: (allowed, reason)
    """

    # Daily loss limit
    daily_pnl = ledger.get_daily_pnl(config)
    loss_limit = config.max_daily_loss_jpy if config.loss_guard_ccy.upper() == "JPY" else config.max_daily_loss_jpy / config.jpy_per_usdt
    if daily_pnl < -loss_limit:
        unit = config.loss_guard_ccy.upper()
        return False, f"Daily loss limit exceeded: loss_{unit.lower()}={daily_pnl:.2f} {unit}, start_{unit.lower()}={0.0:.2f}, equity_{unit.lower()}={daily_pnl:.2f}"

    # Position size limit (check after potential trade)
    if action == 'buy':
        balance = broker.fetch_balance()
        ticker = broker.fetch_ticker(symbol)
        current_pos = balance.get('total', {}).get('BTC', 0.0)
        quote_balance = balance.get('free', {}).get('USDT', 0.0)
        price = ticker['last']
        potential_pos = current_pos + (quote_balance / price * 0.99)  # Estimate
        notional_quote = potential_pos * price
        notional_jpy = notional_quote * config.jpy_per_usdt  # Use config value

        # Check QUOTE limit
        if notional_quote > config.max_position_notional_quote:
            return False, f"Position size limit exceeded: notional_quote={notional_quote:.2f} > max_quote={config.max_position_notional_quote:.2f} USDT"

        # Check JPY limit
        if notional_jpy > config.max_position_notional_jpy:
            return False, f"Position size limit exceeded: notional_jpy={notional_jpy:.2f} > max_jpy={config.max_position_notional_jpy:.2f} JPY"

    # Spread check
    ticker = broker.fetch_ticker(symbol)
    bid = ticker.get('bid', 0)
    ask = ticker.get('ask', 0)
    if bid > 0 and ask > 0:
        spread_bps = ((ask - bid) / bid) * 10000
        if spread_bps > config.max_spread_bps:
            return False, f"Spread too wide: {spread_bps:.2f} bps"

    # Consecutive losses (simplified: recent trades pnl)
    recent_trades = ledger.get_recent_trades(days=1)
    if recent_trades:
        consec_losses = 0
        for trade in reversed(recent_trades[-5:]):  # Last 5
            cost = trade['cost']
            fee = trade['fee']
            side = trade['side']
            # Approximate pnl (simplified)
            if side == 'sell':
                pnl = cost - fee  # Assuming buy was previous
            else:
                pnl = -cost - fee
            if pnl < 0:
                consec_losses += 1
            else:
                break
        if consec_losses >= 3:  # 3 consecutive losses
            return False, f"Consecutive losses: {consec_losses}"

    return True, "OK"