import sys
import os
from pathlib import Path

try:
    import ccxt  # type: ignore
except Exception as e:
    ccxt = None

from trader.config import load_config


def main() -> int:
    config = load_config()
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_file = reports_dir / "auth_smoke_latest.txt"

    if str(getattr(config, "trader_mode", "")).lower() == "paper":
        result = "SKIPPED: paper mode"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(result)
        return 0

    if not config.is_api_configured():
        result = "SKIPPED: api_not_configured"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(result)
        return 0

    if ccxt is None:
        result = "FAIL: ccxt not installed"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(result)
        return 1

    try:
        exchange = ccxt.binance({
            "apiKey": config.ccxt_api_key,
            "secret": config.ccxt_api_secret,
            "sandbox": bool(config.ccxt_sandbox),
            "enableRateLimit": True,
        })

        # Test fetch_balance
        balance = exchange.fetch_balance()
        if not balance:
            raise ValueError("fetch_balance returned empty")

        # Test fetch_ticker
        ticker = exchange.fetch_ticker("BTC/USDT")
        if not ticker or "last" not in ticker:
            raise ValueError("fetch_ticker returned invalid data")

        result = "AUTH_SMOKE: PASS"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(result)
        return 0

    except Exception as e:
        result = f"AUTH_SMOKE: FAIL (reason={str(e)})"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(result)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
