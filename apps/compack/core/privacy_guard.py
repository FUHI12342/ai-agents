from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


_PATTERNS = [
    ("email", re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+"), "<EMAIL_REDACTED>"),
    ("phone", re.compile(r"\b\d{2,4}[- ]?\d{3,4}[- ]?\d{3,4}\b"), "<PHONE_REDACTED>"),
    ("card", re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{3,4}\b"), "<CARD_REDACTED>"),
    ("token", re.compile(r"\b[A-Za-z0-9_\-]{24,}\b"), "<TOKEN_REDACTED>"),
    ("address", re.compile(r"\b\d{3}-\d{4}\b"), "<POSTCODE_REDACTED>"),
]


@dataclass
class GuardResult:
    text: str
    masked: bool
    blocked: bool
    findings: List[str]
    notice: str | None = None


class PrivacyGuard:
    """Lightweight privacy/PII guard."""

    def __init__(self, mode: str = "normal", allow_paths: List[str] | None = None):
        self.mode = (mode or "normal").lower()
        self.allow_paths = allow_paths or []

    def sanitize(self, text: str, *, for_external: bool = False) -> GuardResult:
        """Mask obvious PII/secrets. Block external calls in strict mode when findings remain."""
        if self.mode == "off":
            return GuardResult(text=text, masked=False, blocked=False, findings=[])

        masked_text = text
        findings: List[str] = []
        masked = False

        for name, pattern, replacement in _PATTERNS:
            new_text, count = pattern.subn(replacement, masked_text)
            if count:
                masked_text = new_text
                masked = True
                findings.append(name)

        blocked = False
        notice = None
        if masked and self.mode in {"normal", "strict"}:
            notice = "プライバシー保護のため一部の入力を伏せて処理します。"
        if self.mode == "strict" and for_external and findings:
            blocked = True
            notice = "個人情報らしきものが含まれるため外部送信を止めました。匿名化して再入力してください。"

        return GuardResult(
            text=masked_text,
            masked=masked,
            blocked=blocked,
            findings=findings,
            notice=notice,
        )
