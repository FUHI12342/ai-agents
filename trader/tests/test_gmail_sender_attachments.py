from pathlib import Path

from trader.notify.gmail_sender import build_mime_message


def test_build_mime_message_includes_attachments(tmp_path: Path):
    attach1 = tmp_path / "signals_chart_latest.png"
    attach1.write_bytes(b"pngdata")
    attach2 = tmp_path / "signals_latest.json"
    attach2.write_text("{}", encoding="utf-8")

    msg = build_mime_message(
        subject="s",
        body="b",
        sender="from@example.com",
        to="to@example.com",
        attachments=[attach1, attach2],
    )

    text = msg.as_string()
    assert "signals_chart_latest.png" in text
    assert "signals_latest.json" in text
