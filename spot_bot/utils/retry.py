"""Async retry decorator with exponential backoff.

Usage:
    @async_retry(max_attempts=3, retry_on=(TimeoutError, ConnectionError))
    async def fetch_something():
        ...

The decorator retries on the specified exception types with exponential
backoff (1s, 2s, 4s, ...). On final failure, re-raises the last exception.
`asyncio.CancelledError` is never retried — it always propagates immediately.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from spot_bot.config import RETRY_INITIAL_BACKOFF_S, RETRY_MAX_ATTEMPTS

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def async_retry(
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    initial_backoff: float = RETRY_INITIAL_BACKOFF_S,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    jitter: bool = True,
) -> Callable[[F], F]:
    """Return a decorator that retries an async function with exponential backoff.

    Args:
        max_attempts: Total attempts including the first. 3 = one try + two retries.
        initial_backoff: Seconds to wait before the first retry. Doubles each retry.
        retry_on: Exception types that trigger a retry. Others propagate immediately.
        jitter: Add up to ±25% random jitter to backoff (avoids thundering herd).
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            backoff = initial_backoff
            while True:
                attempt += 1
                try:
                    return await func(*args, **kwargs)
                except asyncio.CancelledError:
                    raise
                except retry_on as e:
                    if attempt >= max_attempts:
                        logger.warning(
                            "%s failed after %d attempts: %s",
                            func.__name__, attempt, e,
                        )
                        raise
                    delay = backoff
                    if jitter:
                        delay *= 1 + random.uniform(-0.25, 0.25)
                    logger.info(
                        "%s attempt %d/%d failed (%s); retrying in %.1fs",
                        func.__name__, attempt, max_attempts, e, delay,
                    )
                    await asyncio.sleep(delay)
                    backoff *= 2

        return wrapper  # type: ignore[return-value]

    return decorator
