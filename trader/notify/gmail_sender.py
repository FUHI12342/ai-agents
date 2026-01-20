from __future__ import annotations

import argparse
import base64
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, Optional

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _build_gmail_service(credentials_path: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Google API libraries missing. Install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        ) from exc

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(f"credentials.json not found: {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def build_mime_message(
    subject: str,
    body: str,
    sender: str,
    to: str,
    attachments: Optional[Iterable[Path]] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject
    msg.set_content(body)

    for p in attachments or []:
        try:
            if not p.exists():
                continue
            ctype, encoding = mimetypes.guess_type(p.name)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(p, "rb") as f:
                data = f.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)
        except Exception:
            # Skip unreadable attachments
            continue

    return msg


def send_gmail(
    subject: str,
    body: str,
    sender: str,
    to: str,
    credentials_path: Path,
    token_path: Path,
    attachments: Optional[Iterable[Path]] = None,
) -> dict:
    service = _build_gmail_service(credentials_path, token_path)

    msg = build_mime_message(subject=subject, body=body, sender=sender, to=to, attachments=attachments)

    encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return (
        service.users()
        .messages()
        .send(userId="me", body={"raw": encoded_message})
        .execute()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Gmail notification (or init token)")
    parser.add_argument("--sender", required=True)
    parser.add_argument("--to", required=True)
    parser.add_argument("--credentials", required=True, help="Path to credentials.json")
    parser.add_argument("--token", required=True, help="Path to token.json")
    parser.add_argument("--subject", default="trader notification")
    parser.add_argument("--body", default="hello")
    parser.add_argument("--init-only", action="store_true", help="Only refresh/create token, do not send")
    args = parser.parse_args()

    credentials_path = Path(args.credentials)
    token_path = Path(args.token)

    if args.init_only:
        _build_gmail_service(credentials_path, token_path)
        print("Token refreshed/created.")
        return 0

    resp = send_gmail(
        subject=args.subject,
        body=args.body,
        sender=args.sender,
        to=args.to,
        credentials_path=credentials_path,
        token_path=token_path,
        attachments=None,
    )
    print(f"Sent: {resp.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
