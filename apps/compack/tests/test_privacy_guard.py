import pytest

from apps.compack.core.privacy_guard import PrivacyGuard


@pytest.mark.unit
def test_privacy_guard_masks_in_normal() -> None:
    guard = PrivacyGuard(mode="normal")
    result = guard.sanitize("contact me at user@example.com or call 090-1234-5678")
    assert "<EMAIL_REDACTED>" in result.text
    assert "<PHONE_REDACTED>" in result.text
    assert result.masked
    assert not result.blocked


@pytest.mark.unit
def test_privacy_guard_blocks_external_in_strict() -> None:
    guard = PrivacyGuard(mode="strict")
    result = guard.sanitize("secret token 123456789012345678901234", for_external=True)
    assert result.blocked
    assert "外部送信を止めました" in (result.notice or "")


@pytest.mark.unit
def test_privacy_guard_off_passes_through() -> None:
    guard = PrivacyGuard(mode="off")
    text = "no pii here"
    result = guard.sanitize(text)
    assert result.text == text
    assert not result.masked
    assert not result.blocked
