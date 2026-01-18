import asyncio
from typing import Any, Dict

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: unit tests for Compack")
    config.addinivalue_line("markers", "property: property-based tests for Compack")


@pytest.fixture
def sample_metadata() -> Dict[str, Any]:
    return {"source": "test"}


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
