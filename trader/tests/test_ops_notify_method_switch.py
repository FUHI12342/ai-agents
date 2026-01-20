import json
from pathlib import Path

import trader.ops_notify as ops_notify


def _write_autorun(reports_dir: Path):
    reports_dir.mkdir(parents=True, exist_ok=True)
    autorun_path = reports_dir / "ops_autorun_latest.json"
    autorun_payload = {"score_pass": True, "gate_pass": True, "gate_ran": True, "eval_days": 3, "score_exit": 0, "gate_exit": 0}
    autorun_path.write_text(json.dumps(autorun_payload), encoding="utf-8")
    return autorun_path


def test_ops_notify_uses_gmail_when_enabled(monkeypatch, tmp_path: Path):
    reports_dir = tmp_path / "reports"
    autorun_path = _write_autorun(reports_dir)
    score_path = reports_dir / "ops_scorecard_latest.txt"
    gate_path = reports_dir / "ops_gate_latest.txt"
    score_path.write_text("score", encoding="utf-8")
    gate_path.write_text("gate", encoding="utf-8")

    state_dir = tmp_path / "state"
    monkeypatch.setenv("TRADER_NOTIFY_METHOD", "gmail")
    monkeypatch.setenv("TRADER_STATE_DIR", str(state_dir))
    monkeypatch.setattr(ops_notify, "STATE_DIR", state_dir)
    monkeypatch.setenv("GMAIL_SENDER", "a@gmail.com")
    monkeypatch.setenv("GMAIL_TO", "b@gmail.com")
    cred_path = tmp_path / "cred.json"
    token_path = tmp_path / "token.json"
    cred_path.write_text("cred", encoding="utf-8")
    token_path.write_text("token", encoding="utf-8")
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(cred_path))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(token_path))

    sent_calls = {}

    def fake_send_gmail(*args, **kwargs):
        sent_calls["called"] = True
        return {"id": "dummy-id"}

    monkeypatch.setattr(ops_notify, "send_gmail", fake_send_gmail)

    # ensure state cleared
    state_file = state_dir / "ops_notify_state.json"
    if state_file.exists():
        state_file.unlink()

    args = [
        "--autorun-json",
        str(autorun_path),
        "--scorecard-txt",
        str(score_path),
        "--gate-txt",
        str(gate_path),
    ]
    ops_notify.main(args)

    assert sent_calls.get("called") is True
    payload = json.loads((reports_dir / "ops_notify_latest.json").read_text(encoding="utf-8"))
    assert payload["method"] == "gmail"
    assert payload["message_id"] == "dummy-id"
    assert payload["body_path"]


def test_ops_notify_fallbacks_to_log_on_gmail_error(monkeypatch, tmp_path: Path):
    reports_dir = tmp_path / "reports"
    autorun_path = _write_autorun(reports_dir)
    score_path = reports_dir / "ops_scorecard_latest.txt"
    gate_path = reports_dir / "ops_gate_latest.txt"
    score_path.write_text("score", encoding="utf-8")
    gate_path.write_text("gate", encoding="utf-8")

    state_dir = tmp_path / "state"
    monkeypatch.setenv("TRADER_NOTIFY_METHOD", "gmail")
    monkeypatch.setenv("TRADER_STATE_DIR", str(state_dir))
    monkeypatch.setattr(ops_notify, "STATE_DIR", state_dir)
    monkeypatch.setenv("GMAIL_SENDER", "a@gmail.com")
    monkeypatch.setenv("GMAIL_TO", "b@gmail.com")
    cred_path = tmp_path / "cred.json"
    token_path = tmp_path / "token.json"
    cred_path.write_text("cred", encoding="utf-8")
    token_path.write_text("token", encoding="utf-8")
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(cred_path))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(token_path))

    def fake_send_gmail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ops_notify, "send_gmail", fake_send_gmail)

    # ensure state cleared
    state_file = state_dir / "ops_notify_state.json"
    if state_file.exists():
        state_file.unlink()

    args = [
        "--autorun-json",
        str(autorun_path),
        "--scorecard-txt",
        str(score_path),
        "--gate-txt",
        str(gate_path),
    ]
    ops_notify.main(args)

    payload = json.loads((reports_dir / "ops_notify_latest.json").read_text(encoding="utf-8"))
    assert payload["method"] == "log"
    assert "boom" in payload.get("reason", "")
    assert payload["body_path"]
