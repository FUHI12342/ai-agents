import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # optional

# プロジェクトのパス
BASE_DIR = Path(__file__).parent

# データ・ログ・モデルの保存先
DATA_DIR = Path(r"D:\ai-data\trader\data")
LOG_DIR = Path(r"D:\ai-data\trader\logs")
MODELS_DIR = Path(r"D:\ai-data\trader\models")

INITIAL_CAPITAL = 10_000  # 最初の資金（円）
FEE_RATE = 0.0005         # 手数料率の仮値

# データ更新開始日（既存データがない場合）
START_DATE = "2017-08-17"  # Binance BTCUSDT 取引開始日

# 旧設定（後方互換）
SYMBOL = os.getenv('TRADER_SYMBOL', 'BTCUSDT')  # デフォルト銘柄
TRADER_SYMBOLS = os.getenv('TRADER_SYMBOLS', '')
SYMBOLS = [s.strip() for s in TRADER_SYMBOLS.split(',') if s.strip()] if TRADER_SYMBOLS else [SYMBOL]

# リスク設定
RISK_CONFIG = {
    "risk_per_trade_pct": 0.5  # 初期値
}

@dataclass
class TraderConfig:
    CONFIRM_REQUIRED: str = "I_UNDERSTAND_LIVE_TRADING_RISK"  # Class variable for confirmation string

    trader_mode: str = 'paper'  # paper|testnet|live
    ccxt_exchange: str = 'binance'
    ccxt_api_key: str = ''
    ccxt_api_secret: str = ''
    ccxt_sandbox: int = 0  # 1 for testnet
    trader_live_confirm: str = ''  # must be CONFIRM_REQUIRED
    trader_symbols: str = 'BTC/USDT'
    capital_amount: float = 10000.0  # 初期資金額
    capital_ccy: str = "JPY"  # "JPY" or "USDT"
    jpy_per_usdt: float = 150.0
    quote_ccy: str = "USDT"  # symbolのquote currency, 現在はUSDT固定
    max_daily_loss_jpy: float = 1000.0
    loss_guard_ccy: str = "JPY"  # "JPY" or "USDT" for daily loss guard
    max_position_notional_quote: float = 100.0  # USDT単位の上限
    max_position_notional_jpy: float = 15000.0  # JPY単位の上限
    max_spread_bps: float = 30.0
    order_timeout_sec: int = 30
    retry_max: int = 3
    retry_base_sec: float = 1.0
    trader_testnet_max_wait_sec: int = 60
    dry_run: bool = False  # True: dry run (注文を飛ばさない)
    allow_market: bool = False  # True: allow market orders

    def __post_init__(self):
        # Load from env if not set explicitly
        for field in self.__dataclass_fields__:
            env_name = field.upper()
            env_value = os.getenv(env_name)
            if env_value is not None:
                setattr(self, field, env_value)

        # Special handling for API keys based on mode
        if self.trader_mode == 'testnet':
            self.ccxt_api_key = os.getenv('BINANCE_TESTNET_API_KEY', self.ccxt_api_key)
            self.ccxt_api_secret = os.getenv('BINANCE_TESTNET_API_SECRET', self.ccxt_api_secret)
            self.ccxt_sandbox = 1
        elif self.trader_mode == 'live':
            self.ccxt_api_key = os.getenv('BINANCE_API_KEY', self.ccxt_api_key)
            self.ccxt_api_secret = os.getenv('BINANCE_API_SECRET', self.ccxt_api_secret)
            self.ccxt_sandbox = 0

        # Type conversions
        self.ccxt_sandbox = int(self.ccxt_sandbox) if isinstance(self.ccxt_sandbox, str) else self.ccxt_sandbox
        self.capital_amount = float(self.capital_amount) if isinstance(self.capital_amount, str) else self.capital_amount
        self.jpy_per_usdt = float(self.jpy_per_usdt) if isinstance(self.jpy_per_usdt, str) else self.jpy_per_usdt
        self.max_daily_loss_jpy = float(self.max_daily_loss_jpy) if isinstance(self.max_daily_loss_jpy, str) else self.max_daily_loss_jpy
        self.max_position_notional_quote = float(self.max_position_notional_quote) if isinstance(self.max_position_notional_quote, str) else self.max_position_notional_quote
        self.max_position_notional_jpy = float(self.max_position_notional_jpy) if isinstance(self.max_position_notional_jpy, str) else self.max_position_notional_jpy
        self.max_spread_bps = float(self.max_spread_bps) if isinstance(self.max_spread_bps, str) else self.max_spread_bps
        self.order_timeout_sec = int(self.order_timeout_sec) if isinstance(self.order_timeout_sec, str) else self.order_timeout_sec
        self.retry_max = int(self.retry_max) if isinstance(self.retry_max, str) else self.retry_max
        self.retry_base_sec = float(self.retry_base_sec) if isinstance(self.retry_base_sec, str) else self.retry_base_sec
        self.trader_testnet_max_wait_sec = int(self.trader_testnet_max_wait_sec) if isinstance(self.trader_testnet_max_wait_sec, str) else self.trader_testnet_max_wait_sec
        if isinstance(self.dry_run, str):
            self.dry_run = self.dry_run.lower() in ('true', '1', 'yes', 'on')
        else:
            self.dry_run = bool(self.dry_run)
        if isinstance(self.allow_market, str):
            self.allow_market = self.allow_market.lower() in ('true', '1', 'yes', 'on')
        else:
            self.allow_market = bool(self.allow_market)

    def initial_quote_balance(self, symbol: str) -> float:
        """Calculate initial quote balance based on capital_ccy"""
        quote = self.infer_quote_ccy(symbol)
        if quote.upper() == "USDT" and self.capital_ccy.upper() == "JPY":
            return self.capital_amount / self.jpy_per_usdt
        return self.capital_amount

    def infer_quote_ccy(self, symbol: str) -> str:
        """Infer quote currency from symbol (e.g., BTCUSDT -> USDT)"""
        # Simple implementation: assume USDT for now, extend later if needed
        if symbol.upper().endswith("USDT"):
            return "USDT"
        elif symbol.upper().endswith("USDJPY"):
            return "JPY"
        else:
            # Default to USDT, but warn
            print(f"[WARN] Unknown symbol format: {symbol}, assuming USDT")
            return "USDT"

    @property
    def is_live_capable(self) -> bool:
        """Check if live trading is possible"""
        return (
            self.trader_mode in ('testnet', 'live') and
            self.trader_live_confirm == "I_UNDERSTAND_LIVE_TRADING_RISK" and
            self.ccxt_api_key and
            self.ccxt_api_secret and
            not self.dry_run  # DRY_RUN時はcapableではない
        )

    @property
    def is_live_armed(self) -> bool:
        """Check if live trading is armed (strict guard for live mode)"""
        return (
            self.trader_mode == 'live' and
            not self.dry_run and
            self.trader_live_confirm == self.CONFIRM_REQUIRED
        )

    def is_api_configured(self) -> bool:
        """Check if API keys are configured (not empty and not containing 'dummy')"""
        if self.trader_mode == 'testnet':
            key = os.getenv('BINANCE_TESTNET_API_KEY', '')
            secret = os.getenv('BINANCE_TESTNET_API_SECRET', '')
        elif self.trader_mode == 'live':
            key = os.getenv('BINANCE_API_KEY', '')
            secret = os.getenv('BINANCE_API_SECRET', '')
        else:
            return True  # paper mode, always True

        return (
            bool(key) and
            bool(secret) and
            'dummy' not in key.lower() and
            'dummy' not in secret.lower()
        )

    @property
    def kill_switch_path(self) -> Path:
        return BASE_DIR.parent / "KILL_SWITCH"

def load_config() -> TraderConfig:
    load_dotenv(BASE_DIR.parent / ".env", override=True)
    return TraderConfig()

# フォルダが無ければ作る
for p in [DATA_DIR, LOG_DIR, MODELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
