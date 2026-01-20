from pathlib import Path

from trader.ops_notify import build_body


def _base_autorun():
    return {"eval_days": 3, "score_exit": 0, "gate_exit": 0}


def test_build_body_without_signals(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    body = build_body(_base_autorun(), reports_dir / "score.txt", reports_dir / "gate.txt", reports_dir)

    assert "Signals last" not in body
    assert "Latest pivot_low" not in body
    assert "Latest buy_signal" not in body


def test_build_body_with_signals(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    signals = {
        "data_last_timestamp_utc": "2026-01-20T01:00:00Z",
        "latest_pivot_low": {"timestamp_utc": "2026-01-19T14:00:00Z", "price": 92700.0},
        "latest_buy_signal": {"timestamp_utc": "2026-01-19T15:00:00Z", "price": 93068.62, "pivot_ref_index": 17990},
    }
    (reports_dir / "signals_latest.json").write_text(
        '{"data_last_timestamp_utc":"2026-01-20T01:00:00Z","latest_pivot_low":{"timestamp_utc":"2026-01-19T14:00:00Z","price":92700.0},"latest_buy_signal":{"timestamp_utc":"2026-01-19T15:00:00Z","price":93068.62,"pivot_ref_index":17990}}',
        encoding="utf-8",
    )

    body = build_body(_base_autorun(), reports_dir / "score.txt", reports_dir / "gate.txt", reports_dir)

    assert "Signals last: 2026-01-20T01:00:00Z" in body
    assert "Latest pivot_low: 2026-01-19T14:00:00Z @ 92700.0" in body
    assert "Latest buy_signal: 2026-01-19T15:00:00Z @ 93068.62 (ref=17990)" in body
