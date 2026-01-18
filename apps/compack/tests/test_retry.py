import pytest

from apps.compack.utils import retry_async


@pytest.mark.property
@pytest.mark.asyncio
async def test_retry_limit_respected() -> None:
    """
    Feature: voice-ai-agent-compack, Property 15: リトライ回数の上限遵守.
    """
    attempts = 0

    async def failing():
        nonlocal attempts
        attempts += 1
        raise ValueError("network error")

    with pytest.raises(ValueError):
        await retry_async(failing, max_attempts=3, base_delay=0)

    assert attempts == 3
