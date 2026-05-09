"""Tests for spot_bot.groq_client — the shared Groq retry helper.

The Groq SDK's behavior is mocked end-to-end here. None of these tests
actually hit the network, so they're fast and deterministic.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spot_bot import groq_client


# Build a minimal fake Groq SDK exception class hierarchy that the
# helper's `from groq import RateLimitError, APIError` will pick up.
# We patch the import inside chat_completion() via sys.modules.
class _FakeAPIError(Exception):
    """Mimics groq.APIError."""


class _FakeRateLimitError(_FakeAPIError):
    """Mimics groq.RateLimitError. Carries an httpx-like .response."""

    def __init__(self, retry_after_seconds=None):
        super().__init__("rate limited")
        self.response = MagicMock()
        if retry_after_seconds is None:
            self.response.headers = {}
        else:
            self.response.headers = {"retry-after": str(retry_after_seconds)}


class _FakeAsyncGroq:
    """Mimics groq.AsyncGroq with a programmable .chat.completions.create."""

    def __init__(self, side_effects):
        # side_effects: list of items returned/raised in order.
        # Strings are returned as content; Exception subclasses are raised.
        self._side_effects = list(side_effects)
        self.calls = 0

        async def _create(**_kwargs):
            self.calls += 1
            if not self._side_effects:
                raise RuntimeError("No more side effects configured")
            effect = self._side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            choice = MagicMock()
            choice.message.content = effect
            resp = MagicMock()
            resp.choices = [choice]
            return resp

        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = _create

    def __init_call_count__(self):
        return self.calls


def _patch_groq_module(monkeypatch, fake_client_factory):
    """Install a fake `groq` module so the helper's lazy import picks it up."""
    import sys
    fake_module = MagicMock()
    fake_module.AsyncGroq = fake_client_factory
    fake_module.RateLimitError = _FakeRateLimitError
    fake_module.APIError = _FakeAPIError
    monkeypatch.setitem(sys.modules, "groq", fake_module)


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_key")


@pytest.mark.asyncio
async def test_succeeds_on_first_try(with_api_key, monkeypatch):
    instances: list[_FakeAsyncGroq] = []

    def factory(api_key):
        client = _FakeAsyncGroq(side_effects=["Hello translated"])
        instances.append(client)
        return client

    _patch_groq_module(monkeypatch, factory)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "test prompt", max_tokens=10, log_tag="test",
    )
    assert result == "Hello translated"
    assert instances[0].calls == 1
    sleep_mock.assert_not_called()


@pytest.mark.asyncio
async def test_retries_on_rate_limit_then_succeeds(with_api_key, monkeypatch):
    instances: list[_FakeAsyncGroq] = []

    def factory(api_key):
        client = _FakeAsyncGroq(side_effects=[
            _FakeRateLimitError(retry_after_seconds=1),
            _FakeRateLimitError(retry_after_seconds=2),
            "Final result",
        ])
        instances.append(client)
        return client

    _patch_groq_module(monkeypatch, factory)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "p", max_tokens=10, log_tag="test",
    )
    assert result == "Final result"
    assert instances[0].calls == 3
    # Two sleeps for the two 429s
    assert sleep_mock.await_count == 2
    sleep_args = [c.args[0] for c in sleep_mock.await_args_list]
    assert sleep_args[0] == 1.0
    assert sleep_args[1] == 2.0


@pytest.mark.asyncio
async def test_gives_up_after_max_retries(with_api_key, monkeypatch):
    instances: list[_FakeAsyncGroq] = []

    def factory(api_key):
        # 4 attempts total = 1 initial + 3 retries = 4 errors before giving up
        client = _FakeAsyncGroq(side_effects=[
            _FakeRateLimitError(retry_after_seconds=1),
            _FakeRateLimitError(retry_after_seconds=1),
            _FakeRateLimitError(retry_after_seconds=1),
            _FakeRateLimitError(retry_after_seconds=1),
        ])
        instances.append(client)
        return client

    _patch_groq_module(monkeypatch, factory)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "p", max_tokens=10, log_tag="test",
    )
    assert result is None
    assert instances[0].calls == groq_client._MAX_RETRIES + 1
    # Sleeps happen between attempts 1→2, 2→3, 3→4 (i.e. _MAX_RETRIES sleeps)
    assert sleep_mock.await_count == groq_client._MAX_RETRIES


@pytest.mark.asyncio
async def test_returns_none_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # Even if a fake module is installed, the helper should bail before importing it.
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "p", max_tokens=10, log_tag="test",
    )
    assert result is None
    sleep_mock.assert_not_called()


@pytest.mark.asyncio
async def test_caps_sleep_at_max(with_api_key, monkeypatch):
    instances: list[_FakeAsyncGroq] = []

    def factory(api_key):
        client = _FakeAsyncGroq(side_effects=[
            _FakeRateLimitError(retry_after_seconds=9999),  # absurd value
            "Recovered",
        ])
        instances.append(client)
        return client

    _patch_groq_module(monkeypatch, factory)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "p", max_tokens=10, log_tag="test",
    )
    assert result == "Recovered"
    sleep_args = [c.args[0] for c in sleep_mock.await_args_list]
    assert sleep_args == [groq_client._MAX_SLEEP_SECONDS]


@pytest.mark.asyncio
async def test_default_backoff_when_no_retry_after_header(with_api_key, monkeypatch):
    instances: list[_FakeAsyncGroq] = []

    def factory(api_key):
        client = _FakeAsyncGroq(side_effects=[
            _FakeRateLimitError(retry_after_seconds=None),  # no header
            "OK",
        ])
        instances.append(client)
        return client

    _patch_groq_module(monkeypatch, factory)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(groq_client.asyncio, "sleep", sleep_mock)

    result = await groq_client.chat_completion(
        "p", max_tokens=10, log_tag="test",
    )
    assert result == "OK"
    assert sleep_mock.await_args_list[0].args[0] == groq_client._DEFAULT_BACKOFF_SECONDS
