from pathlib import Path
import time

from trader.ops_scorecard import parse_log_guards


def test_parse_log_guards_limits_to_window(tmp_path: Path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    old_log = logs_dir / "run_dev_daily_20251231.log"
    recent_log = logs_dir / "run_dev_daily_20260101.log"

    old_log.write_text("[GUARD] old\n", encoding="utf-8")
    recent_log.write_text("[GUARD] recent\n", encoding="utf-8")

    # ensure mtimes differ
    old_time = time.time() - 5 * 86400
    recent_time = time.time()
    for f, t in [(old_log, old_time), (recent_log, recent_time)]:
        f.touch()
        Path(f).chmod(f.stat().st_mode)
        import os
        os.utime(f, (t, t))

    days = ["20260101", "20260102"]
    count = parse_log_guards(logs_dir, days)
    assert count == 1
