import sys
import os
import smtplib
import argparse
import traceback
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from .config import LOG_DIR
import uuid

def send_report(session: str, to_addr: str, strict: bool = False):
    """
    指定されたセッションのレポートをGmailで送信する。
    """
    # レポートファイルパス
    date_str = datetime.now().strftime("%Y%m%d")
    report_path = LOG_DIR / f"report_{date_str}_{session}_multi.txt"

    if not report_path.exists():
        if strict:
            raise FileNotFoundError(f"Report file not found: {report_path}")
        else:
            print(f"SKIP: Report file not found: {report_path}")
            return

    # レポート内容読み込み
    report_content = report_path.read_text(encoding="utf-8")

    # Gmail設定
    gmail_user = os.getenv("GMAIL_USER")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    # 資格情報取得を堅牢化
    if gmail_user and gmail_app_password:
        # 方式1: 別々の環境変数
        pass
    elif gmail_user and ':' in gmail_user:
        # 方式2: GMAIL_USER が "email:app_password" の形式
        parts = gmail_user.split(':', 1)
        if len(parts) == 2:
            gmail_user, gmail_app_password = parts
        else:
            gmail_user = None
            gmail_app_password = None
    else:
        gmail_user = None
        gmail_app_password = None

    if not gmail_user or not gmail_app_password:
        if strict:
            raise ValueError("missing creds")
        else:
            print("SKIP: missing creds")
            return

    # メール作成
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_addr
    msg['Subject'] = f"Trading Report - {session} ({date_str})"
    # split の直参照を避ける
    domain_parts = gmail_user.split('@', 1)
    domain = domain_parts[1] if len(domain_parts) == 2 else 'gmail.com'
    msg['Message-ID'] = f"<{uuid.uuid4()}@{domain}>"

    # 本文
    body = f"""
自動生成トレードレポート - {session}

{report_content}
"""
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # SMTP送信
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_app_password)
        text = msg.as_string()
        result = server.sendmail(gmail_user, to_addr, text)
        server.quit()
        print(f"GMAIL_SEND_SUCCESS: Report sent successfully to {to_addr}, MessageId: {msg['Message-ID']}")
    except Exception as e:
        print(f"GMAIL_SEND_FAILED: Failed to send email: {e}", file=sys.stderr)
        raise RuntimeError(f"Failed to send email: {e}")

def main() -> int:
    parser = argparse.ArgumentParser(description='Send daily trading report via Gmail')
    parser.add_argument('session', help='Session name (e.g., morning, night)')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--strict', action='store_true', help='Exit with error on missing report or credentials')

    args = parser.parse_args()

    try:
        send_report(args.session, args.to, args.strict)
        return 0
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())