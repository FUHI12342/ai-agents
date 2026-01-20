from pathlib import Path

from trader.ops_notify import build_body, write_body_latest


def _base_autorun():
    return {"eval_days": 3, "score_exit": 0, "gate_exit": 0}


def test_body_file_written_with_signals(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    signals_path = reports_dir / "signals_latest.json"
    signals_path.write_text(
        '{"data_last_timestamp_utc":"2026-01-20T01:00:00Z","latest_pivot_low":{"timestamp_utc":"2026-01-19T14:00:00Z","price":92700.0},"latest_buy_signal":{"timestamp_utc":"2026-01-19T15:00:00Z","price":93068.62,"pivot_ref_index":17990}}',
        encoding="utf-8",
    )

    body = build_body(_base_autorun(), reports_dir / "score.txt", reports_dir / "gate.txt", reports_dir)
    body_path = write_body_latest(reports_dir, body)

    content = body_path.read_text(encoding="utf-8")
    assert "Signals last: 2026-01-20T01:00:00Z" in content
    assert "Latest pivot_low: 2026-01-19T14:00:00Z @ 92700.0" in content
    assert "Latest buy_signal: 2026-01-19T15:00:00Z @ 93068.62 (ref=17990)" in content


def test_body_file_without_signals(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    body = build_body(_base_autorun(), reports_dir / "score.txt", reports_dir / "gate.txt", reports_dir)
    body_path = write_body_latest(reports_dir, body)
    content = body_path.read_text(encoding="utf-8")

    assert "Signals last" not in content
    assert "Latest pivot_low" not in content
    assert "Latest buy_signal" not in content
