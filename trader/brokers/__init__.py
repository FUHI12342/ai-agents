from typing import Optional
from pathlib import Path

from ..config import TraderConfig, load_config
from .base import Broker
from .paper import PaperBroker
from .ccxt_live import CCXTBroker

def create_broker(config: Optional[TraderConfig] = None) -> Broker:
    if config is None:
        config = load_config()

    if config.trader_mode == 'paper':
        return PaperBroker(config)
    elif config.trader_mode in ('testnet', 'live'):
        if not config.is_live_capable:
            raise ValueError("Live trading not configured properly. Check TRADER_LIVE_CONFIRM and API keys.")
        return CCXTBroker(config)
    else:
        raise ValueError(f"Unknown trader_mode: {config.trader_mode}")