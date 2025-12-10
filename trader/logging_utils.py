import json
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR

def append_backtest_log(symbol: str, stats: dict):
    """バックテスト結果を1行JSONでログに追記する"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    path = LOG_DIR / f"backtest_{date_str}.log"

    record = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        **stats,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return path  # ログファイルのパスを返す
