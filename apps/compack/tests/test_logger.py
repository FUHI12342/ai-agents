import json

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from apps.compack.core import StructuredLogger


@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(message=st.text(min_size=1, max_size=30))
def test_structured_logger_has_required_fields(capsys: pytest.CaptureFixture[str], message: str) -> None:
    """
    Feature: voice-ai-agent-compack, Property 13: 構造化ログの完備性.
    Logs must include timestamp, level, logger name, and message event.
    """
    logger = StructuredLogger(log_file=None, level="INFO")
    logger.info(message, module="test_logger")

    output = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(output)

    assert "timestamp" in data
    assert "level" in data
    assert "logger" in data
    assert data["event"] == message


@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(secret_value=st.text(min_size=5, max_size=20))
def test_structured_logger_masks_secrets(capsys: pytest.CaptureFixture[str], secret_value: str) -> None:
    """
    Feature: voice-ai-agent-compack, Property 14: 秘匿情報のマスキング.
    Secret-like fields must be redacted from logs.
    """
    logger = StructuredLogger(log_file=None, level="INFO")
    logger.info("mask-test", api_key=secret_value, nested={"token": secret_value})

    output = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(output)

    assert data["api_key"] == "***"
    assert data["nested"]["token"] == "***"
    assert secret_value not in output
