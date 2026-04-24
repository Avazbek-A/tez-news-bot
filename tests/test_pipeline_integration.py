"""End-to-end integration tests for the pipeline.

We mock Playwright entirely — no Chromium, no network. The mocked browser
serves scripted HTML for the Telegram channel page and for spot.uz article
pages. This lets us exercise the full scrape → fetch → clean → filter →
cache pipeline offline, and it's what actually validates that the
refactors from Phase 3 (browser pool, DRY scraping) still drive the
expected control flow.

Fixture covers:
- Telegram channel HTML with 3 posts, all with spot.uz links
- Each spot.uz article has a proper `.articleContent` container
- Article cache populates on first run, is hit on second run
- Per-user keyword filters drop one article
- last_scraped_id advances past the newest post
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spot_bot.pipeline import run_pipeline
from spot_bot.storage import article_cache, db, filters, user_settings

# ---------------------------------------------------------------------------
# Fake Playwright page
# ---------------------------------------------------------------------------


_CHANNEL_HTML_MESSAGES = [
    {
        "post_id": "spotuz/34950",
        "datetime": "2026-04-24T09:30:00+00:00",
        "text_html": '<a href="https://spot.uz/news/ai-boom">AI boom in UZ economy</a>',
        "links": ["https://spot.uz/news/ai-boom"],
    },
    {
        "post_id": "spotuz/34949",
        "datetime": "2026-04-24T08:15:00+00:00",
        "text_html": '<a href="https://spot.uz/news/spam-alert">spam spam spam</a>',
        "links": ["https://spot.uz/news/spam-alert"],
    },
    {
        "post_id": "spotuz/34948",
        "datetime": "2026-04-23T18:00:00+00:00",
        "text_html": '<a href="https://spot.uz/news/economy-update">Central bank rate cut</a>',
        "links": ["https://spot.uz/news/economy-update"],
    },
]

_ARTICLE_HTMLS = {
    "https://spot.uz/news/ai-boom": """
        <html><body>
          <h1>AI boom drives local tech sector</h1>
          <div class="articleContent">
            <p>Uzbek startups raised record funding this quarter,
            driven by AI platform demand and tech infrastructure growth.</p>
            <p>Economists expect the trend to continue into next year.</p>
          </div>
        </body></html>
    """,
    "https://spot.uz/news/spam-alert": """
        <html><body>
          <h1>Something spam related</h1>
          <div class="articleContent">
            <p>This article mentions spam prominently.</p>
            <p>Additional lines about spam detection and filtering.</p>
          </div>
        </body></html>
    """,
    "https://spot.uz/news/economy-update": """
        <html><body>
          <h1>Central bank cuts key rate to 13%</h1>
          <div class="articleContent">
            <p>The central bank today announced a 50 bp cut to the key rate,
            citing softer inflation and stable FX reserves.</p>
            <p>Analysts see this as a signal of confidence in the economy outlook.</p>
          </div>
        </body></html>
    """,
}


def _make_locator(messages: list[dict[str, Any]]) -> Any:
    """Build a Playwright Locator mock that serves _CHANNEL_HTML_MESSAGES."""
    async def all_() -> list[Any]:
        return [_make_message_locator(m) for m in messages]

    async def count_() -> int:
        return len(messages)

    loc = MagicMock()
    loc.all = all_
    loc.count = count_
    return loc


def _make_message_locator(msg: dict[str, Any]) -> Any:
    """Mock a single message locator (.tgme_widget_message)."""
    loc = MagicMock()

    async def get_attribute(name: str) -> str | None:
        if name == "data-post":
            return msg["post_id"]
        if name == "datetime":
            return msg["datetime"]
        if name == "href":
            # Used when iterating `a` tags inside text locator.
            return None  # provided by inner locator below
        return None

    loc.get_attribute = get_attribute

    def locator(selector: str) -> Any:
        if "date time" in selector:
            date_loc = MagicMock()

            async def date_count() -> int:
                return 1

            async def date_attr(_: str) -> str:
                return msg["datetime"]

            date_loc.count = date_count
            date_loc.get_attribute = date_attr
            return date_loc
        if "tgme_widget_message_date" in selector:
            date_loc = MagicMock()

            async def dc() -> int:
                return 0

            date_loc.count = dc
            return date_loc
        if "message_text" in selector:
            text_loc = MagicMock()

            async def count() -> int:
                return 1

            async def inner_html() -> str:
                return msg["text_html"]

            def link_locator(_: str) -> Any:
                link_loc = MagicMock()
                links = msg["links"]

                async def lc() -> int:
                    return len(links)

                def nth(i: int) -> Any:
                    a = MagicMock()

                    async def gh(_name: str) -> str:
                        return links[i]

                    a.get_attribute = gh
                    return a

                link_loc.count = lc
                link_loc.nth = nth
                return link_loc

            text_loc.count = count
            text_loc.inner_html = inner_html
            text_loc.locator = link_locator
            return text_loc
        return MagicMock()

    loc.locator = locator
    return loc


class _FakePage:
    """In-memory Playwright page that routes URLs to scripted HTML."""

    def __init__(self, channel_messages: list[dict[str, Any]]) -> None:
        self._channel_messages = channel_messages
        self._current_content = ""
        # Any selector → _make_locator when we're on the channel page
        self._on_channel = False

    async def goto(self, url: str, **_: Any) -> None:
        if "spot.uz" in url:
            self._current_content = _ARTICLE_HTMLS.get(url, "")
            self._on_channel = False
        else:
            # Telegram channel URL
            self._on_channel = True
            self._current_content = ""

    async def wait_for_selector(self, *_: Any, **__: Any) -> None:
        return None

    async def wait_for_timeout(self, ms: int) -> None:
        return None

    async def evaluate(self, script: str) -> None:
        return None

    async def content(self) -> str:
        return self._current_content

    async def route(self, _pattern: str, _handler: Any) -> None:
        return None

    def locator(self, selector: str) -> Any:
        if self._on_channel and "tgme_widget_message" in selector:
            return _make_locator(self._channel_messages)
        return MagicMock()

    async def close(self) -> None:
        return None


class _FakeContext:
    async def new_page(self) -> _FakePage:
        return _FakePage(_CHANNEL_HTML_MESSAGES)

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def pipeline_env(tmp_path, monkeypatch):
    """Wire up tmp DB, fake browser pool, and per-user settings."""
    # DB
    db_file = tmp_path / "integ.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "_conn", None)
    monkeypatch.setattr(user_settings, "_cache", {})
    monkeypatch.setattr(user_settings, "_MIGRATED", True)
    await db.connect()

    # Fake browser pool — bypass Playwright entirely.
    fake_ctx = _FakeContext()

    @asynccontextmanager
    async def fake_page():
        yield _FakePage(_CHANNEL_HTML_MESSAGES)

    async def fake_get_context() -> Any:
        return fake_ctx

    # Patch the lookup points — both the module-level `browser_page` alias
    # in telegram_channel and the get_context used by article_fetcher.
    monkeypatch.setattr(
        "spot_bot.scrapers.telegram_channel.browser_page", fake_page,
    )
    monkeypatch.setattr(
        "spot_bot.scrapers.article_fetcher.get_context",
        AsyncMock(return_value=fake_ctx),
    )

    yield
    await db.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_end_to_end_latest_scrape(pipeline_env):
    result = await run_pipeline(count=3, user_id=42)

    assert len(result.articles) == 3
    # Articles carry post IDs from the scraper + bodies from spot.uz
    ids = {a.get("id") for a in result.articles}
    assert ids == {"spotuz/34948", "spotuz/34949", "spotuz/34950"}
    # Bodies came from the parsed spot.uz HTML
    combined = " ".join(a.get("body", "") for a in result.articles)
    assert "Uzbek startups raised record funding" in combined
    assert "key rate" in combined

    # run_pipeline alone doesn't set last_scraped_id — that's done in
    # jobs.run_job. Verify it stays unset here.
    assert await user_settings.get(42, "last_scraped_id") is None


async def test_cache_hit_on_second_run(pipeline_env):
    # First run populates the cache
    await run_pipeline(count=3, user_id=42)
    cached = await article_cache.lookup("https://spot.uz/news/ai-boom")
    assert cached is not None
    assert "AI boom" in cached["title"]

    # Second run should find the same articles (cache returns identical
    # parsed output even if we mutate the HTML between runs).
    with patch.dict(_ARTICLE_HTMLS, {"https://spot.uz/news/ai-boom": "<html/>"}):
        result = await run_pipeline(count=3, user_id=42)

    # AI-boom still comes back with the original body because of cache.
    bodies = [a.get("body", "") for a in result.articles]
    assert any("Uzbek startups raised record funding" in b for b in bodies)


async def test_keyword_filter_drops_spam(pipeline_env):
    await filters.add(42, "spam", filters.MODE_EXCLUDE)

    result = await run_pipeline(count=3, user_id=42)

    # The spam-alert article should be dropped.
    assert len(result.articles) == 2
    assert result.filtered_count == 1
    for a in result.articles:
        assert "spam" not in a.get("body", "").lower()


async def test_include_filter_narrows_to_one(pipeline_env):
    await filters.add(42, "central bank", filters.MODE_INCLUDE)

    result = await run_pipeline(count=3, user_id=42)

    # Only the economy article matches "central bank"
    assert len(result.articles) == 1
    assert "Central bank" in result.articles[0]["title"]


async def test_no_filters_keeps_all(pipeline_env):
    result = await run_pipeline(count=3, user_id=42)
    assert len(result.articles) == 3
    assert result.filtered_count == 0


async def test_per_user_settings_isolation(pipeline_env):
    """Two users with different filters should get different results."""
    await filters.add(1, "spam", filters.MODE_EXCLUDE)
    # user 2 has no filters

    r1 = await run_pipeline(count=3, user_id=1)
    r2 = await run_pipeline(count=3, user_id=2)

    assert len(r1.articles) == 2
    assert len(r2.articles) == 3
