"""Tests for the httpx + selectolax telegram channel scraper.

Uses a stored HTML fixture (one real page from t.me/s/spotuz) rather than
hitting the network, so tests are deterministic and fast.
"""
from pathlib import Path

import pytest

from spot_bot.scrapers.telegram_channel import (
    _extract_posts_from_html,
    _latest_post_id_from_html,
    _post_sort_key,
)


FIXTURE = Path(__file__).parent / "fixtures" / "tme_spotuz_latest.html"


@pytest.fixture
def sample_html():
    return FIXTURE.read_text(encoding="utf-8")


def test_extract_posts_returns_data(sample_html):
    processed = set()
    out = _extract_posts_from_html(sample_html, processed)
    assert len(out) >= 5, "fixture should have at least 5 posts"
    for post_data, numeric_id in out:
        assert post_data["id"].startswith("spotuz/")
        assert numeric_id is not None
        assert numeric_id == int(post_data["id"].split("/")[-1])
        assert post_data["date"]  # ISO date string
        assert "links" in post_data
        assert "has_spot_link" in post_data


def test_extract_skips_already_processed(sample_html):
    processed = set()
    first = _extract_posts_from_html(sample_html, processed)
    assert len(first) > 0
    # Second call with same processed set should return zero
    second = _extract_posts_from_html(sample_html, processed)
    assert second == []


def test_latest_post_id_extracted(sample_html):
    latest = _latest_post_id_from_html(sample_html)
    assert latest is not None
    assert isinstance(latest, int)
    assert latest > 30000  # Spotuz IDs are well above this


def test_post_sort_key_ascending(sample_html):
    processed = set()
    out = _extract_posts_from_html(sample_html, processed)
    posts = [post for post, _ in out]
    posts_sorted = sorted(posts, key=_post_sort_key)
    ids_asc = [int(p["id"].split("/")[-1]) for p in posts_sorted]
    assert ids_asc == sorted(ids_asc)


def test_handles_empty_html():
    assert _extract_posts_from_html("", set()) == []
    assert _extract_posts_from_html("<html></html>", set()) == []
    assert _latest_post_id_from_html("") is None


def test_links_extracted_from_post_text(sample_html):
    processed = set()
    out = _extract_posts_from_html(sample_html, processed)
    # At least one post in the fixture should have a spot.uz link
    has_spot = any(p["has_spot_link"] for p, _ in out)
    assert has_spot, "fixture should contain at least one post with a spot.uz link"
