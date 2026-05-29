"""Tests that the scraper and article fetcher never silently drop a post
due to transient failures.

The trust requirement: a news item must not vanish because of a single
network blip, a rate-limit (429), a transient 5xx, an odd/missing date,
or an empty caption. These tests verify the retry + no-drop behavior.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import pytest

import spot_bot.scrapers.telegram_channel as tc
import spot_bot.scrapers.article_fetcher as af
import spot_bot.scrapers.http_retry as hr


# ---------- Fakes ----------

class _Resp:
    def __init__(self, status_code=200, text="<html>ok</html>", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class _ScriptedClient:
    """httpx-like client that returns/raises from a scripted sequence.

    Each item is either a _Resp, or an Exception instance to raise.
    """
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    async def get(self, url):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Make all backoff sleeps instant so retry tests run fast.

    Both scrapers now share http_retry, so patching its backoff helpers
    neutralizes sleeps everywhere.
    """
    monkeypatch.setattr(hr, "backoff_seconds", lambda attempt, **kw: 0.0)
    monkeypatch.setattr(hr, "retry_after_seconds", lambda resp, attempt, **kw: 0.0)


# ---------- _fetch_page (channel pages) ----------

@pytest.mark.asyncio
async def test_fetch_page_retries_429_then_succeeds():
    client = _ScriptedClient([
        _Resp(status_code=429),
        _Resp(status_code=503),
        _Resp(status_code=200, text="<html>good</html>"),
    ])
    out = await tc._fetch_page(client, "http://x")
    assert out == "<html>good</html>"
    assert client.calls == 3  # two retries then success


@pytest.mark.asyncio
async def test_fetch_page_retries_timeout_then_succeeds():
    client = _ScriptedClient([
        httpx.TimeoutException("t"),
        httpx.ConnectError("net"),
        _Resp(status_code=200, text="<html>recovered</html>"),
    ])
    out = await tc._fetch_page(client, "http://x")
    assert out == "<html>recovered</html>"
    assert client.calls == 3


@pytest.mark.asyncio
async def test_fetch_page_does_not_retry_404():
    """Permanent status — retrying can't help, so bail immediately."""
    client = _ScriptedClient([
        _Resp(status_code=404),
        _Resp(status_code=200, text="should-not-reach"),
    ])
    out = await tc._fetch_page(client, "http://x")
    assert out is None
    assert client.calls == 1  # no retry on 404


@pytest.mark.asyncio
async def test_fetch_page_gives_up_after_max_retries():
    """Persistent 503 across all attempts → None, but only after
    exhausting the full retry budget (never gives up early)."""
    client = _ScriptedClient([_Resp(status_code=503)] * (tc._HTTP_RETRIES + 1))
    out = await tc._fetch_page(client, "http://x")
    assert out is None
    assert client.calls == tc._HTTP_RETRIES + 1


@pytest.mark.asyncio
async def test_fetch_page_honors_retry_after_header(monkeypatch):
    """A 429 with Retry-After is retried (header parsing path)."""
    seen = {}

    def fake_retry_after(resp, attempt, **kw):
        seen["ra"] = resp.headers.get("Retry-After")
        return 0.0

    monkeypatch.setattr(hr, "retry_after_seconds", fake_retry_after)
    client = _ScriptedClient([
        _Resp(status_code=429, headers={"Retry-After": "1"}),
        _Resp(status_code=200, text="<html>ok</html>"),
    ])
    out = await tc._fetch_page(client, "http://x")
    assert out == "<html>ok</html>"
    assert seen["ra"] == "1"


# ---------- Undated posts must not be dropped ----------

def test_undated_post_kept_with_default_date():
    html = """
    <div class="tgme_widget_message" data-post="spotuz/999">
      <div class="tgme_widget_message_text js-message_text">
        Breaking news with no date element
      </div>
    </div>
    """
    processed: set = set()
    batch = tc._extract_posts_from_html(html, processed)
    assert len(batch) == 1
    post, numeric_id = batch[0]
    assert numeric_id == 999
    # Defaulted to today rather than dropped
    assert post["date"] == datetime.now().date().isoformat()


def test_dated_post_still_parses_normally():
    html = """
    <div class="tgme_widget_message" data-post="spotuz/1000">
      <div class="tgme_widget_message_date">
        <time datetime="2026-05-01T10:00:00+00:00">May 1</time>
      </div>
      <div class="tgme_widget_message_text js-message_text">Dated post</div>
    </div>
    """
    processed: set = set()
    batch = tc._extract_posts_from_html(html, processed)
    assert len(batch) == 1
    assert batch[0][0]["date"] == "2026-05-01"


# ---------- _get_article_html (spot.uz article) ----------

@pytest.mark.asyncio
async def test_get_article_html_retries_5xx_then_succeeds():
    client = _ScriptedClient([
        _Resp(status_code=502),
        _Resp(status_code=200, text="<html>article</html>"),
    ])
    out = await af._get_article_html(client, "http://spot.uz/a")
    assert out == "<html>article</html>"
    assert client.calls == 2


@pytest.mark.asyncio
async def test_get_article_html_retries_timeout_then_succeeds():
    client = _ScriptedClient([
        httpx.TimeoutException("t"),
        _Resp(status_code=200, text="<html>article</html>"),
    ])
    out = await af._get_article_html(client, "http://spot.uz/a")
    assert out == "<html>article</html>"


@pytest.mark.asyncio
async def test_get_article_html_bails_on_404():
    client = _ScriptedClient([_Resp(status_code=404)])
    out = await af._get_article_html(client, "http://spot.uz/a")
    assert out is None
    assert client.calls == 1


@pytest.mark.asyncio
async def test_get_article_html_gives_up_after_retries():
    client = _ScriptedClient([httpx.TimeoutException("t")] * (af._FETCH_RETRIES + 1))
    out = await af._get_article_html(client, "http://spot.uz/a")
    assert out is None
    assert client.calls == af._FETCH_RETRIES + 1


# ---------- Article still kept when fetch fails (post not lost) ----------

@pytest.mark.asyncio
async def test_post_survives_when_article_fetch_fully_fails():
    """spot.uz fetch fails every retry → falls back to Telegram caption,
    post is NOT dropped."""
    post = {
        "id": "spotuz/555",
        "date": "2026-05-09T00:00:00",
        "text_html": "Telegram caption text here",
        "links": ["https://www.spot.uz/ru/2026/05/09/x/"],
        "has_spot_link": True,
        "tg_photos": [],
    }
    client = _ScriptedClient([httpx.TimeoutException("t")] * (af._FETCH_RETRIES + 1))
    sem = asyncio.Semaphore(1)
    result = await af._process_post(client, post, sem, include_images=True)
    assert result["id"] == "spotuz/555"
    assert result["source"] == "telegram_fallback"
    assert result["body"]  # non-empty


# ---------- Empty-caption fallback uses title so post survives filter ----------

def test_fallback_body_uses_title_when_caption_empty():
    out = af._telegram_fallback("", "2026-01-01", [], title="Headline only",
                                post_id="spotuz/7")
    assert out["body"] == "Headline only"


def test_fallback_body_prefers_caption_when_present():
    out = af._telegram_fallback("Caption text", "2026-01-01", [],
                                title="Headline", post_id="spotuz/7")
    assert out["body"] == "Caption text"


def test_fallback_body_empty_when_no_content():
    out = af._telegram_fallback("", "2026-01-01", [], title="", post_id="spotuz/7")
    assert out["body"] == ""


# ---------- Partial-scrape flag (B3) ----------

@pytest.mark.asyncio
async def test_scrape_latest_sets_partial_on_initial_fetch_failure(monkeypatch):
    """If the very first page fetch fails, scrape_latest flags the run as
    partial via the stats dict (so the delivery card can warn)."""
    async def fail_fetch(client, url):
        return None

    monkeypatch.setattr(tc, "_fetch_page", fail_fetch)
    stats = {}
    posts = await tc.scrape_latest(10, stats=stats)
    assert posts == []
    assert stats.get("partial") is True


@pytest.mark.asyncio
async def test_scrape_latest_no_partial_on_clean_run(monkeypatch):
    """A normal run leaves the stats dict without a partial flag."""
    page = (
        '<div class="tgme_widget_message" data-post="spotuz/5">'
        '<div class="tgme_widget_message_date">'
        '<time datetime="2026-05-01T10:00:00+00:00">May 1</time></div>'
        '<div class="tgme_widget_message_text js-message_text">Hi</div>'
        '</div>'
    )
    calls = {"n": 0}

    async def one_page(client, url):
        # Serve the page once, then act like end-of-channel (empty).
        calls["n"] += 1
        return page if calls["n"] == 1 else ""

    monkeypatch.setattr(tc, "_fetch_page", one_page)
    stats = {}
    posts = await tc.scrape_latest(1, stats=stats)
    assert len(posts) == 1
    assert stats.get("partial") is not True
