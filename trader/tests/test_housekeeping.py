from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from trader.housekeeping import Rule, collect_deletes


def test_housekeeping_collect_deletes(tmp_path: Path):
    root = tmp_path / "ai-agents"
    (root / "scripts/logs").mkdir(parents=True)
    (root / "reports").mkdir(parents=True)

    old = root / "scripts/logs" / "daily_run_20250101_000000.log"
    new = root / "scripts/logs" / "daily_run_20260106_000000.log"
    old.write_text("old")
    new.write_text("new")

    now = datetime(2026, 1, 6, 0, 0, 0)
    # old を 40日前に
    old_ts = now.timestamp() - 60 * 60 * 24 * 40
    os.utime(old, (old_ts, old_ts))
    os.utime(new, (now.timestamp(), now.timestamp()))

    rules = [Rule("scripts/logs/daily_run_*.log", keep_days=30)]
    deletes = collect_deletes(root, rules, now)

    assert old in deletes
    assert new not in deletes