"""Tests for the AI summarize module.

We don't hit the real Claude API — we mock the Anthropic client. The tests
cover cache round-trips, graceful no-op when the key is missing, and
concurrent batch summarization.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spot_bot.ai import summarize
from spot_bot.storage import db


@pytest.fixture
async def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "_conn", None)
    await db.connect()
    yield
    await db.close()


# ---------------------------------------------------------------------------


def test_is_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert summarize.is_available() is False


def test_is_available_true_with_key_and_sdk(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Pretend the SDK is importable
    fake_anthropic = MagicMock()
    with patch.dict("sys.modules", {"anthropic": fake_anthropic}):
        assert summarize.is_available() is True


async def test_summarize_batch_noop_without_key(monkeypatch, fresh_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    articles = [{"id": "spotuz/1", "title": "T", "body": "some body text"}]
    await summarize.summarize_batch(articles, lang="en")
    # No summary key added
    assert "summary" not in articles[0]


async def test_summarize_batch_empty_list(fresh_db, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    # Even without SDK, empty list returns early before any checks
    await summarize.summarize_batch([], lang="en")


async def test_summarize_cache_hit(monkeypatch, fresh_db):
    """Second call with the same article should hit the cache and skip API."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    # Pre-populate cache manually
    await summarize._ensure_cache_table()
    await summarize._store("spotuz/1", "en", "A cached summary.")

    # Mock anthropic — but it should NOT be called.
    api_calls = {"n": 0}
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = lambda **_: (
        api_calls.__setitem__("n", api_calls["n"] + 1) or MagicMock()
    )
    fake_mod = MagicMock(Anthropic=MagicMock(return_value=fake_client))
    with patch.dict("sys.modules", {"anthropic": fake_mod}):
        articles = [{"id": "spotuz/1", "title": "t", "body": "b"}]
        await summarize.summarize_batch(articles, lang="en")

    assert articles[0]["summary"] == "A cached summary."
    assert api_calls["n"] == 0


async def test_summarize_stores_new_summaries(monkeypatch, fresh_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    await summarize._ensure_cache_table()

    # Build a mock response that looks like anthropic's Message
    text_block = MagicMock()
    text_block.text = "Generated summary for the test."
    mock_response = MagicMock()
    mock_response.content = [text_block]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = mock_response
    fake_mod = MagicMock(Anthropic=MagicMock(return_value=fake_client))

    with patch.dict("sys.modules", {"anthropic": fake_mod}):
        articles = [
            {"id": "spotuz/10", "title": "T1", "body": "body one"},
            {"id": "spotuz/11", "title": "T2", "body": "body two"},
        ]
        await summarize.summarize_batch(articles, lang="en")

    assert articles[0]["summary"] == "Generated summary for the test."
    assert articles[1]["summary"] == "Generated summary for the test."
    # Both got cached
    assert await summarize._lookup("spotuz/10", "en") == "Generated summary for the test."
    assert await summarize._lookup("spotuz/11", "en") == "Generated summary for the test."


async def test_summarize_skips_articles_without_id(monkeypatch, fresh_db):
    """Articles with no post ID don't break the batch."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    await summarize._ensure_cache_table()

    text_block = MagicMock()
    text_block.text = "Sum."
    mock_response = MagicMock(content=[text_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = mock_response
    fake_mod = MagicMock(Anthropic=MagicMock(return_value=fake_client))

    with patch.dict("sys.modules", {"anthropic": fake_mod}):
        articles = [
            {"title": "No ID", "body": "x"},  # no id — skipped for caching
            {"id": "spotuz/5", "title": "Yes ID", "body": "y"},
        ]
        await summarize.summarize_batch(articles, lang="en")

    # The one with an ID got cached; the one without still got summarized in-place
    # but was not written to the cache.
    assert articles[1].get("summary") == "Sum."
    assert await summarize._lookup("spotuz/5", "en") == "Sum."


def test_model_default(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    assert summarize._model() == summarize._DEFAULT_MODEL


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-5")
    assert summarize._model() == "claude-opus-4-5"


async def test_summarize_uses_configured_model(monkeypatch, fresh_db):
    """The model id passed to Anthropic should come from ANTHROPIC_MODEL."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    await summarize._ensure_cache_table()

    text_block = MagicMock()
    text_block.text = "s."
    mock_response = MagicMock(content=[text_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = mock_response
    fake_mod = MagicMock(Anthropic=MagicMock(return_value=fake_client))

    with patch.dict("sys.modules", {"anthropic": fake_mod}):
        await summarize.summarize_batch(
            [{"id": "spotuz/1", "title": "t", "body": "b"}], lang="en",
        )

    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-5"


async def test_summarize_per_language_cache(monkeypatch, fresh_db):
    """The same post in different languages has separate cache entries."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    await summarize._ensure_cache_table()
    await summarize._store("spotuz/1", "en", "English summary.")
    await summarize._store("spotuz/1", "ru", "Русский пересказ.")

    assert await summarize._lookup("spotuz/1", "en") == "English summary."
    assert await summarize._lookup("spotuz/1", "ru") == "Русский пересказ."
    assert await summarize._lookup("spotuz/1", "uz") is None
