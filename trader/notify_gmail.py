from __future__ import annotations

import argparse
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

def send_gmail(to: str, subject: str, body: str, from_email: Optional[str] = None) -> int:
    user = os.environ.get("GMAIL_USER")
    app_pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not app_pw:
        print("Missing env vars: GMAIL_USER and/or GMAIL_APP_PASSWORD")
        return 2

    from_email = from_email or user

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, app_pw)
            s.send_message(msg)
        print("OK: sent")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 1

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body-file")
    p.add_argument("--body-encoding", default="utf-8")
    p.add_argument("--body", default=None)
    p.add_argument("--from-email", default=None)
    args = p.parse_args()

    if args.body is not None:
        body_text = args.body
    elif args.body_file:
        with open(args.body_file, "r", encoding=args.body_encoding) as f:
            body_text = f.read()
    else:
        body_text = ""

    return send_gmail(args.to, args.subject, body_text, args.from_email)

if __name__ == "__main__":
    raise SystemExit(main())

