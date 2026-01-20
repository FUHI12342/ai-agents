from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

DATE_FMT = "%Y%m%d"


def last_n_completed_dates(days: int, include_today: bool = False) -> List[str]:
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc).date()
    start = 0 if include_today else 1
    return [(today - timedelta(days=i)).strftime(DATE_FMT) for i in range(start, start + days)]


def _extract_symbol_date(path: Path) -> Optional[Tuple[str, str]]:
    parts = path.stem.split("_")
    if len(parts) < 3:
        return None
    symbol = parts[1].upper()
    date = parts[2]
    if not date.isdigit():
        return None
    return symbol, date


def discover_daily_coverage(
    data_dir: Path,
    max_days: int,
    include_today: bool,
    allowed_symbols: Set[str],
) -> Dict[str, object]:
    target_days = last_n_completed_dates(max_days, include_today=include_today)
    covered: Set[str] = set()
    for path in data_dir.glob("daily_*.json"):
        parsed = _extract_symbol_date(path)
        if not parsed:
            continue
        symbol, date = parsed
        if date not in target_days:
            continue
        if allowed_symbols and symbol not in allowed_symbols:
            continue
        covered.add(date)

    coverage_count = len(covered)
    eval_days: Optional[int]
    if coverage_count >= max_days:
        eval_days = max_days
    elif coverage_count >= 3:
        eval_days = coverage_count
    else:
        eval_days = None

    return {
        "target_days": target_days,
        "covered_days": sorted(covered),
        "coverage_count": coverage_count,
        "eval_days": eval_days,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover eval window from daily_*.json coverage")
    parser.add_argument("--data-dir", default=os.getenv("TRADER_DATA_DIR", "data"), help="Data directory containing daily_*.json")
    parser.add_argument("--max-days", type=int, default=7, help="Max lookback days (default 7)")
    parser.add_argument("--include-today", action="store_true", help="Include today in coverage window")
    args = parser.parse_args()

    allowed = {s.strip().upper() for s in os.getenv("TRADER_ALLOWED_SYMBOLS", "BTCUSDT").split(",") if s.strip()}
    data_dir = Path(args.data_dir)
    result = discover_daily_coverage(
        data_dir=data_dir,
        max_days=args.max_days,
        include_today=args.include_today,
        allowed_symbols=allowed,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
