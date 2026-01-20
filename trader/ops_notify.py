from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from trader.config import REPORTS_DIR
from trader.notify.gmail_sender import send_gmail

DEFAULT_TZ = os.getenv("TRADER_TZ", "Asia/Tokyo")
STATE_DIR = Path(os.getenv("TRADER_STATE_DIR", "state"))


def now_local():
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(DEFAULT_TZ))
        except Exception:
            pass
    return datetime.now()


def today_local_str() -> str:
    return now_local().strftime("%Y%m%d")


def read_json(path: Path) -> Dict:
    try:
        text = path.read_text(encoding="utf-8")
        if text.startswith("\ufeff"):
            text = text.lstrip("\ufeff")
        return json.loads(text)
    except Exception:
        return {}


def already_notified(state_path: Path) -> bool:
    if not state_path.exists():
        return False
    data = read_json(state_path)
    return data.get("last_notified_date") == today_local_str()


def write_state(state_path: Path) -> None:
    payload = {"last_notified_date": today_local_str()}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def send_log_notification(subject: str, body: str) -> Dict:
    print(f"[NOTIFY] {subject}")
    return {"method": "log", "sent": True, "message": body, "subject": subject}


def try_send_gmail(subject: str, body: str, attachments: list[Path]) -> Dict:
    sender = os.getenv("GMAIL_SENDER")
    recipient = os.getenv("GMAIL_TO")
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
    token_path = os.getenv("GMAIL_TOKEN_PATH")

    missing_env = [k for k, v in {
        "GMAIL_SENDER": sender,
        "GMAIL_TO": recipient,
        "GMAIL_CREDENTIALS_PATH": credentials_path,
        "GMAIL_TOKEN_PATH": token_path,
    }.items() if not v]
    if missing_env:
        return {"method": "gmail", "sent": False, "reason": f"missing_env:{','.join(missing_env)}"}

    cred_path_obj = Path(credentials_path)
    token_path_obj = Path(token_path)
    if not cred_path_obj.exists():
        return {"method": "gmail", "sent": False, "reason": f"missing_file:{cred_path_obj}"}
    if not token_path_obj.exists():
        return {"method": "gmail", "sent": False, "reason": f"missing_file:{token_path_obj}"}

    try:
        resp = send_gmail(
            subject=subject,
            body=body,
            sender=sender,
            to=recipient,
            credentials_path=cred_path_obj,
            token_path=token_path_obj,
            attachments=attachments,
        )
        message_id = resp.get("id") or resp.get("threadId", "")
        return {"method": "gmail", "sent": True, "message_id": message_id}
    except Exception as exc:
        reason = str(exc)
        if len(reason) > 200:
            reason = reason[:200]
        return {"method": "gmail", "sent": False, "reason": reason}


def build_subject(date_str: str) -> str:
    return f"TRADER DEV: READY (score PASS & gate PASS) - {date_str}"


def append_signals_summary(lines, reports_dir: Path) -> None:
    signals_path = reports_dir / "signals_latest.json"
    if not signals_path.exists():
        return
    signals = read_json(signals_path)
    if not signals:
        return

    last_ts = signals.get("data_last_timestamp_utc")
    latest_pivot = signals.get("latest_pivot_low") or {}
    latest_buy = signals.get("latest_buy_signal") or {}

    if last_ts:
        lines.append(f"Signals last: {last_ts}")
    pivot_ts = latest_pivot.get("timestamp_utc")
    pivot_price = latest_pivot.get("price")
    if pivot_ts and pivot_price is not None:
        lines.append(f"Latest pivot_low: {pivot_ts} @ {pivot_price}")
    buy_ts = latest_buy.get("timestamp_utc")
    buy_price = latest_buy.get("price")
    buy_ref = latest_buy.get("pivot_ref_index")
    if buy_ts and buy_price is not None:
        suffix = f" (ref={int(buy_ref)})" if buy_ref is not None else ""
        lines.append(f"Latest buy_signal: {buy_ts} @ {buy_price}{suffix}")


def build_body(autorun: Dict, score_txt: Path, gate_txt: Path, reports_dir: Path) -> str:
    lines = []
    lines.append("Score PASS & Gate PASS")
    lines.append(f"eval_days: {autorun.get('eval_days')}")
    lines.append(f"score_exit: {autorun.get('score_exit')}")
    lines.append(f"gate_exit: {autorun.get('gate_exit')}")
    lines.append(f"scorecard: {score_txt}")
    lines.append(f"gate: {gate_txt}")
    append_signals_summary(lines, reports_dir)
    lines.append("")
    lines.append("This is a notification only. No live orders are sent.")
    return "\n".join(lines)


def write_body_latest(reports_dir: Path, body: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "ops_notify_body_latest.txt"
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(body, encoding="utf-8")
    tmp_path.replace(out_path)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Notify when score & gate pass (paper-only)")
    parser.add_argument("--autorun-json", default=str(REPORTS_DIR / "ops_autorun_latest.json"))
    parser.add_argument("--scorecard-txt", default=str(REPORTS_DIR / "ops_scorecard_latest.txt"))
    parser.add_argument("--gate-txt", default=str(REPORTS_DIR / "ops_gate_latest.txt"))
    parser.add_argument("--dry-run", action="store_true", help="Do not write state")
    args = parser.parse_args(argv)

    autorun_path = Path(args.autorun_json)
    autorun = read_json(autorun_path)
    if not autorun:
        print(f"[INFO] autorun empty. path={autorun_path}")
        return 0
    if not (autorun.get("score_pass") and autorun.get("gate_pass") and autorun.get("gate_ran")):
        print("[INFO] score/gate not both PASS; skip notify")
        return 0

    state_path = STATE_DIR / "ops_notify_state.json"
    if already_notified(state_path):
        print("[INFO] already notified today; skip")
        return 0

    reports_dir = Path(args.autorun_json).parent if args.autorun_json else REPORTS_DIR
    subject = build_subject(today_local_str())
    body = build_body(autorun, Path(args.scorecard_txt), Path(args.gate_txt), reports_dir)
    body_path = write_body_latest(reports_dir, body)

    attachments: list[Path] = []
    chart_path = reports_dir / "signals_chart_latest.png"
    signals_path = reports_dir / "signals_latest.json"
    if chart_path.exists():
        attachments.append(chart_path)
    if signals_path.exists():
        attachments.append(signals_path)

    notify_method = os.getenv("TRADER_NOTIFY_METHOD", "log").lower()
    result = {}
    fallback_reason = ""
    if notify_method == "gmail":
        result = try_send_gmail(subject, body, attachments)
        if not result.get("sent"):
            fallback_reason = result.get("reason", "")
            result = send_log_notification(subject, body)
            result["method"] = "log"
            result["reason"] = fallback_reason
    else:
        result = send_log_notification(subject, body)

    notify_payload = {
        "sent": result.get("sent", False),
        "method": result.get("method"),
        "reason": result.get("reason", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "message_id": result.get("message_id", ""),
        "body_path": str(body_path),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    notify_path = reports_dir / "ops_notify_latest.json"
    notify_path.write_text(json.dumps(notify_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if result.get("sent") and not args.dry_run:
        write_state(state_path)

    print(f"[INFO] Notification result: {notify_payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
