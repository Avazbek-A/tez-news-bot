"""Tests for the intentional post/article filters (skip-seen + mute).

These drops are user-chosen and must be COUNTED (so the delivery card can
report them) — never silent. Tests assert both the kept set and the
returned counts.
"""
from __future__ import annotations

import pytest

from spot_bot.cleaners.filters import (
    filter_posts,
    mute_articles,
    _numeric_id,
    _matches_currency,
)


def _post(pid, text="", links=None):
    return {
        "id": pid,
        "text_html": text,
        "links": links or [],
        "has_spot_link": bool(links),
    }


# ---------- _numeric_id ----------

def test_numeric_id_parses_trailing_int():
    assert _numeric_id("spotuz/37764") == 37764


def test_numeric_id_non_numeric_returns_none():
    assert _numeric_id("kun_uz/abc123") is None
    assert _numeric_id("") is None
    assert _numeric_id(None) is None


# ---------- skip-seen ----------

def test_skip_seen_drops_delivered_ids():
    posts = [_post("spotuz/100"), _post("spotuz/101"), _post("spotuz/102")]
    kept, skipped, muted = filter_posts(
        posts, delivered_ids={101}, skip_seen=True,
    )
    assert [p["id"] for p in kept] == ["spotuz/100", "spotuz/102"]
    assert skipped == 1
    assert muted == 0


def test_skip_seen_disabled_keeps_all():
    posts = [_post("spotuz/100"), _post("spotuz/101")]
    kept, skipped, muted = filter_posts(
        posts, delivered_ids={100, 101}, skip_seen=False,
    )
    assert len(kept) == 2
    assert skipped == 0


def test_skip_seen_no_delivered_keeps_all():
    posts = [_post("spotuz/100")]
    kept, skipped, _ = filter_posts(posts, delivered_ids=set(), skip_seen=True)
    assert len(kept) == 1
    assert skipped == 0


def test_skip_seen_preserves_order():
    posts = [_post(f"spotuz/{i}") for i in (200, 201, 202, 203)]
    kept, _, _ = filter_posts(posts, delivered_ids={201}, skip_seen=True)
    assert [p["id"] for p in kept] == ["spotuz/200", "spotuz/202", "spotuz/203"]


# ---------- mute currency ----------

def test_mute_currency_by_url_slug():
    posts = [
        _post("spotuz/1", links=["https://www.spot.uz/ru/2026/05/08/currency-exchange/"]),
        _post("spotuz/2", links=["https://www.spot.uz/ru/2026/05/08/hong-kong/"]),
    ]
    kept, _, muted = filter_posts(posts, mute_currency=True)
    assert [p["id"] for p in kept] == ["spotuz/2"]
    assert muted == 1


def test_mute_currency_by_caption_text():
    posts = [
        _post("spotuz/1", text="Курс валют в Узбекистане на сегодня"),
        _post("spotuz/2", text="Новый завод открылся в Ташкенте"),
    ]
    kept, _, muted = filter_posts(posts, mute_currency=True)
    assert [p["id"] for p in kept] == ["spotuz/2"]
    assert muted == 1


def test_mute_currency_disabled_keeps_currency():
    posts = [_post("spotuz/1", text="Курс валют сегодня")]
    kept, _, muted = filter_posts(posts, mute_currency=False)
    assert len(kept) == 1
    assert muted == 0


# ---------- mute keywords ----------

def test_mute_keywords_drops_matching():
    posts = [
        _post("spotuz/1", text="Tariff hike announced"),
        _post("spotuz/2", text="Tech startup raises funding"),
    ]
    kept, _, muted = filter_posts(posts, muted_keywords=["tariff"])
    assert [p["id"] for p in kept] == ["spotuz/2"]
    assert muted == 1


def test_mute_keywords_case_insensitive():
    posts = [_post("spotuz/1", text="BIG TARIFF NEWS")]
    kept, _, muted = filter_posts(posts, muted_keywords=["tariff"])
    assert kept == []
    assert muted == 1


# ---------- combined: skip-seen + mute counted separately ----------

def test_skip_and_mute_counted_separately():
    posts = [
        _post("spotuz/1"),                                   # kept
        _post("spotuz/2"),                                   # skipped (seen)
        _post("spotuz/3", text="курс валют"),                # muted
    ]
    kept, skipped, muted = filter_posts(
        posts, delivered_ids={2}, skip_seen=True, mute_currency=True,
    )
    assert [p["id"] for p in kept] == ["spotuz/1"]
    assert skipped == 1
    assert muted == 1


def test_seen_takes_precedence_over_mute():
    """A post that is both seen and muted counts once, as seen (checked
    first), so totals don't double-count."""
    posts = [_post("spotuz/5", text="курс валют")]
    kept, skipped, muted = filter_posts(
        posts, delivered_ids={5}, skip_seen=True, mute_currency=True,
    )
    assert kept == []
    assert skipped == 1
    assert muted == 0


# ---------- mute_articles (post-fetch safety net) ----------

def test_mute_articles_currency_by_title():
    arts = [
        {"title": "Курс валют в Узбекистане", "body": "..."},
        {"title": "Новый банк", "body": "..."},
    ]
    kept, muted = mute_articles(arts, mute_currency=True)
    assert [a["title"] for a in kept] == ["Новый банк"]
    assert muted == 1


def test_mute_articles_keyword_in_body():
    arts = [
        {"title": "Economy", "body": "The new tariff will raise prices"},
        {"title": "Sports", "body": "Match results"},
    ]
    kept, muted = mute_articles(arts, muted_keywords=["tariff"])
    assert [a["title"] for a in kept] == ["Sports"]
    assert muted == 1


def test_mute_articles_noop_when_nothing_configured():
    arts = [{"title": "Курс валют", "body": "x"}]
    kept, muted = mute_articles(arts, mute_currency=False, muted_keywords=[])
    assert len(kept) == 1
    assert muted == 0


def test_matches_currency_multilingual():
    assert _matches_currency("Valyuta kurslari", None)
    assert _matches_currency("Today's currency rate", None)
    assert not _matches_currency("A normal headline", None)


# ---------- Pipeline-level: counts propagate to PipelineResult ----------

@pytest.mark.asyncio
async def test_pipeline_propagates_skip_and_mute_counts(monkeypatch):
    """End-to-end through run_pipeline (with scrape/fetch mocked): an
    already-seen post and a currency post are filtered, and both counts
    land on PipelineResult so the delivery card can show them."""
    import spot_bot.pipeline as pl

    settings = {
        "channel_url": "https://t.me/s/spotuz",
        "skip_seen": True,
        "delivered_post_ids": [101],          # post 101 already seen
        "mute_currency": True,
        "muted_keywords": [],
        "include_ads": False,
        "translate_to": None,
        "enable_summaries": False,
        "quality_threshold": 0,               # disable quality filter
        "dup_threshold": 100,                 # disable dedupe
        "topics": [],
        "language": "en",
    }
    monkeypatch.setattr(pl, "get_setting", lambda k: settings.get(k))
    # Single source → takes the scrape_latest path.
    monkeypatch.setattr(
        pl, "get_sources",
        lambda: [{"id": "default", "type": "telegram", "url": settings["channel_url"]}],
    )

    fake_posts = [
        {"id": "spotuz/100", "text_html": "Normal news", "links": [], "has_spot_link": False},
        {"id": "spotuz/101", "text_html": "Seen news", "links": [], "has_spot_link": False},
        {"id": "spotuz/102", "text_html": "Курс валют",
         "links": ["https://www.spot.uz/ru/2026/05/08/currency-exchange/"],
         "has_spot_link": True},
    ]

    async def fake_scrape_latest(count, **kw):
        return list(fake_posts)

    async def fake_fetch_articles(posts, **kw):
        # One article per surviving post.
        return [
            {"id": p["id"], "title": "T", "body": "Body text here", "images": []}
            for p in posts
        ]

    monkeypatch.setattr(pl, "scrape_latest", fake_scrape_latest)
    monkeypatch.setattr(pl, "fetch_articles", fake_fetch_articles)
    monkeypatch.setattr(pl, "clean_batch", lambda arts, include_ads=False: arts)

    result = await pl.run_pipeline(count=10)

    # post 101 skipped (seen), post 102 muted (currency) → only 100 survives
    assert result.skipped_seen_count == 1
    assert result.muted_count == 1
    assert [a["id"] for a in result.articles] == ["spotuz/100"]
    assert result.partial is False
