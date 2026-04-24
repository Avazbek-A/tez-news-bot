"""Tests for the async_retry decorator."""

import asyncio

import pytest

from spot_bot.utils.retry import async_retry


async def test_succeeds_first_try():
    calls = 0

    @async_retry(max_attempts=3, initial_backoff=0.01)
    async def ok():
        nonlocal calls
        calls += 1
        return "ok"

    assert await ok() == "ok"
    assert calls == 1


async def test_retries_then_succeeds():
    calls = 0

    @async_retry(max_attempts=3, initial_backoff=0.01)
    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("nope")
        return "done"

    assert await flaky() == "done"
    assert calls == 3


async def test_gives_up_after_max_attempts():
    calls = 0

    @async_retry(max_attempts=3, initial_backoff=0.01)
    async def always_fails():
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await always_fails()
    assert calls == 3


async def test_only_retries_listed_exceptions():
    calls = 0

    @async_retry(
        max_attempts=3, initial_backoff=0.01,
        retry_on=(TimeoutError,),
    )
    async def wrong_type():
        nonlocal calls
        calls += 1
        raise ValueError("not a timeout")

    with pytest.raises(ValueError):
        await wrong_type()
    assert calls == 1  # Did not retry — ValueError is not in retry_on


async def test_never_retries_cancelled_error():
    calls = 0

    @async_retry(max_attempts=5, initial_backoff=0.01)
    async def cancelled():
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await cancelled()
    assert calls == 1  # CancelledError propagates immediately
