import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Paths
BASE_DIR = Path(__file__).parent
DATA_ROOT = Path(os.getenv("TRADER_DATA_ROOT", r"D:\ai-data\trader"))
DATA_DIR = Path(os.getenv("TRADER_DATA_DIR", DATA_ROOT / "data"))
LOG_DIR = Path(os.getenv("TRADER_LOG_DIR", DATA_ROOT / "logs"))
REPORTS_DIR = Path(os.getenv("TRADER_REPORTS_DIR", DATA_ROOT / "reports"))
STATE_DIR = Path(os.getenv("TRADER_STATE_DIR", DATA_ROOT / "state"))
MODELS_DIR = Path(os.getenv("TRADER_MODELS_DIR", DATA_ROOT / "models"))

INITIAL_CAPITAL = 10_000
FEE_RATE = 0.0005
START_DATE = "2017-08-17"  # Binance BTCUSDT start date

SYMBOL = os.getenv("TRADER_SYMBOL", "BTCUSDT")
TRADER_SYMBOLS = os.getenv("TRADER_SYMBOLS", "")
SYMBOLS: List[str] = [s.strip() for s in TRADER_SYMBOLS.split(",") if s.strip()] if TRADER_SYMBOLS else [SYMBOL]

RISK_CONFIG = {"risk_per_trade_pct": 0.5}


@dataclass
class TraderConfig:
    CONFIRM_REQUIRED: str = "I_UNDERSTAND_LIVE_TRADING_RISK"

    trader_mode: str = "paper"  # paper|testnet|live
    trader_exchange_env: str = "testnet"  # testnet|live
    ccxt_exchange: str = "binance"
    ccxt_api_key: str = ""
    ccxt_api_secret: str = ""
    ccxt_sandbox: int = 0
    trader_live_confirm: str = ""
    trader_symbols: str = "BTC/USDT"
    capital_amount: float = 10000.0
    capital_ccy: str = "JPY"
    jpy_per_usdt: float = 150.0
    quote_ccy: str = "USDT"
    max_daily_loss_jpy: float = 1000.0
    loss_guard_ccy: str = "JPY"
    max_position_notional_quote: float = 100.0
    max_position_notional_jpy: float = 15000.0
    max_spread_bps: float = 30.0
    order_timeout_sec: int = 30
    retry_max: int = 3
    retry_base_sec: float = 1.0
    trader_testnet_max_wait_sec: int = 60
    dry_run: bool = False
    allow_market: bool = False

    def __post_init__(self):
        env_env = os.getenv("ENV", "dev").lower()
        for field_name, field_def in self.__dataclass_fields__.items():  # type: ignore
            if not field_def.init:
                continue
            env_name = field_name.upper()
            env_value = os.getenv(env_name)
            if env_value is None:
                continue
            current = getattr(self, field_name)
            try:
                if isinstance(current, bool):
                    setattr(self, field_name, env_value.lower() in ("1", "true", "yes", "on"))
                elif isinstance(current, int):
                    setattr(self, field_name, int(env_value))
                elif isinstance(current, float):
                    setattr(self, field_name, float(env_value))
                else:
                    setattr(self, field_name, env_value)
            except Exception:
                setattr(self, field_name, env_value)

        if env_env == "dev" and str(self.trader_mode).lower() == "live":
            raise RuntimeError("LIVE forbidden in dev ENV")

        exch_env = str(self.trader_exchange_env).lower()
        if exch_env not in ("testnet", "live"):
            exch_env = "testnet"
        self.trader_exchange_env = exch_env

        if self.trader_exchange_env == "testnet":
            self.ccxt_api_key = os.getenv("BINANCE_TESTNET_API_KEY", self.ccxt_api_key)
            self.ccxt_api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", self.ccxt_api_secret)
            self.ccxt_sandbox = 1
        elif self.trader_mode == "live" or self.trader_exchange_env == "live":
            self.ccxt_api_key = os.getenv("BINANCE_API_KEY", self.ccxt_api_key)
            self.ccxt_api_secret = os.getenv("BINANCE_API_SECRET", self.ccxt_api_secret)
            self.ccxt_sandbox = 0

    def initial_quote_balance(self, symbol: str) -> float:
        quote = self.infer_quote_ccy(symbol)
        if quote.upper() == "USDT" and self.capital_ccy.upper() == "JPY":
            return float(self.capital_amount) / float(self.jpy_per_usdt)
        return float(self.capital_amount)

    def infer_quote_ccy(self, symbol: str) -> str:
        if symbol.upper().endswith("USDT"):
            return "USDT"
        elif symbol.upper().endswith("USDJPY"):
            return "JPY"
        return "USDT"

    @property
    def is_live_armed(self) -> bool:
        return (
            str(self.trader_mode).lower() == "live"
            and not bool(self.dry_run)
            and str(self.trader_live_confirm) == self.CONFIRM_REQUIRED
        )

    def is_api_configured(self) -> bool:
        if str(self.trader_mode).lower() == "paper":
            return True
        key = str(self.ccxt_api_key or "")
        secret = str(self.ccxt_api_secret or "")
        if "dummy" in key.lower() or "dummy" in secret.lower():
            return False
        return bool(key and secret)

    @property
    def kill_switch_path(self) -> Path:
        return BASE_DIR.parent / "KILL_SWITCH"


def load_config() -> TraderConfig:
    return TraderConfig()


for p in (DATA_DIR, LOG_DIR, REPORTS_DIR, STATE_DIR, MODELS_DIR):
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
