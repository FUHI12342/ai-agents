from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable, TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: Iterable[type[BaseException]] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Retry an async function with exponential backoff."""
    attempt = 0
    while True:
        try:
            return await func()
        except tuple(exceptions) as exc:  # type: ignore[arg-type]
            attempt += 1
            if attempt >= max_attempts:
                raise
            if on_retry:
                on_retry(attempt, exc)
            await asyncio.sleep(base_delay * attempt)
