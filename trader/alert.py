#!/usr/bin/env python3
"""
Alert system for trader notifications
"""

import os
import time
from pathlib import Path
from typing import Optional

from .config import BASE_DIR
from .notify_gmail import send_gmail

def send_alert_once(subject: str, body: str, to: Optional[str] = None) -> bool:
    """
    Send alert email once per day to avoid spam.
    Returns True if sent, False if already sent today.
    """
    today = time.strftime('%Y%m%d')
    from .config import REPORTS_DIR
    flag_file = REPORTS_DIR / f"alert_sent_{today}.flag"

    if flag_file.exists():
        print(f"[ALERT] Already sent today: {flag_file}")
        return False

    try:
        if to is None:
            to = os.getenv('TRADER_ALERT_EMAIL', '')
        if not to:
            print("[ALERT] No alert email configured")
            return False

        send_gmail(to=to, subject=subject, body=body)
        flag_file.write_text(f"Sent at {time.strftime('%Y-%m-%d %H:%M:%S')}\nSubject: {subject}")
        print(f"[ALERT] Sent: {subject}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")
        # Do not raise, just log and return False to not break trading logic
        return False