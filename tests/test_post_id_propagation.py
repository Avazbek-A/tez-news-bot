"""Tests that the Telegram channel post id flows through every fetch
return path, so downstream display layers (inline text, .txt file,
voice caption, chapter list, bookmark/share buttons, translation
cache) can render `#<post_id>`.

The bug this guards against: article_fetcher used to build article
dicts without an `id` field, so article.get("id", "") returned ""
everywhere downstream and post IDs vanished from delivery output.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from spot_bot.scrapers import article_fetcher as af


def _make_post(post_id="spotuz/12345", has_link=True, tg_photos=None):
    return {
        "id": post_id,
        "date": "2026-05-09T00:00:00",
        "text_html": "Some text <a href='https://www.spot.uz/x'>x</a>",
        "links": ["https://www.spot.uz/ru/2026/05/09/x/"] if has_link else [],
        "has_spot_link": has_link,
        "tg_photos": tg_photos or [],
    }


# ---------- No spot.uz link path (telegram-only post) ----------

@pytest.mark.asyncio
async def test_id_preserved_telegram_only_post():
    post = _make_post(has_link=False)
    sem = asyncio.Semaphore(1)
    client = MagicMock()
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"
    assert result["source"] == "telegram"


# ---------- HTTP-error fallback paths ----------

@pytest.mark.asyncio
async def test_id_preserved_on_nav_error():
    post = _make_post()
    sem = asyncio.Semaphore(1)
    client = MagicMock()
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"
    assert result["source"] == "telegram_fallback"


@pytest.mark.asyncio
async def test_id_preserved_on_http_non_200():
    post = _make_post()
    sem = asyncio.Semaphore(1)
    resp = MagicMock(status_code=500, text="bad")
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"


@pytest.mark.asyncio
async def test_id_preserved_on_empty_body():
    post = _make_post()
    sem = asyncio.Semaphore(1)
    resp = MagicMock(status_code=200, text="")
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"


# ---------- Successful clean parse ----------

@pytest.mark.asyncio
async def test_id_preserved_on_successful_parse(monkeypatch):
    post = _make_post()
    sem = asyncio.Semaphore(1)
    resp = MagicMock(status_code=200,
                     text="<html><body><h1>Title</h1>"
                          "<div class='articleContent'>"
                          "<p>" + ("a" * 200) + "</p>"
                          "</div></body></html>")
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)

    # Stub the cleaner so we don't depend on the html_cleaner internals
    monkeypatch.setattr(
        af, "clean_html",
        lambda content, base_url="": ("Headline", "Body text", []),
    )

    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"
    assert result["source"] == "spot.uz"
    assert result["title"] == "Headline"


@pytest.mark.asyncio
async def test_id_preserved_when_clean_returns_no_body(monkeypatch):
    post = _make_post()
    sem = asyncio.Semaphore(1)
    resp = MagicMock(status_code=200, text="<html>auth wall</html>")
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr(
        af, "clean_html",
        lambda content, base_url="": ("Headline", None, []),
    )
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/12345"
    # Falls back to telegram_fallback, but id is still there
    assert result["source"] == "telegram_fallback"


# ---------- _telegram_fallback helper ----------

def test_telegram_fallback_includes_id():
    out = af._telegram_fallback("text", "2026-01-01", [], post_id="spotuz/99")
    assert out["id"] == "spotuz/99"


def test_telegram_fallback_default_id_is_empty():
    out = af._telegram_fallback("text", "2026-01-01", [])
    assert out["id"] == ""


# ---------- Post id renders in display layers ----------

def test_extract_post_id_telegram_format():
    from spot_bot.delivery import telegram_sender as ts
    assert ts._extract_post_id({"id": "spotuz/35808"}) == "35808"


def test_extract_post_id_no_slash_returns_empty():
    from spot_bot.delivery import telegram_sender as ts
    assert ts._extract_post_id({"id": "noslash"}) == ""


def test_extract_post_id_non_numeric_suffix_returns_empty():
    """RSS articles use <source>/<hash>, not a Telegram post number.
    Don't display a fake "#abc123" as if it were a post id."""
    from spot_bot.delivery import telegram_sender as ts
    assert ts._extract_post_id({"id": "kun_uz/abc123"}) == ""


def test_extract_post_id_missing_returns_empty():
    from spot_bot.delivery import telegram_sender as ts
    assert ts._extract_post_id({}) == ""
