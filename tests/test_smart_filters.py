"""Tests for the quality / topic / duplicate filters in pipeline.py."""
import pytest

from spot_bot.pipeline import _apply_smart_filters
from spot_bot import settings


@pytest.fixture
def fake_settings(monkeypatch):
    """Yields a dict that test bodies fill; pipeline.get_setting reads from it."""
    overrides: dict = {}

    def fake_get(k):
        if k in overrides:
            return overrides[k]
        return settings._DEFAULTS.get(k)

    monkeypatch.setattr("spot_bot.pipeline.get_setting", fake_get)
    return overrides


def _set(fake_settings, key, value):
    fake_settings[key] = value


def _articles(*pairs):
    return [{"id": f"src/{i}", "title": t, "body": b}
            for i, (t, b) in enumerate(pairs, start=1)]


def test_quality_filter_drops_short_articles(fake_settings):
    _set(fake_settings, "quality_threshold", 100)
    arts = _articles(("Long enough", "x" * 200), ("Too short", "x" * 50))
    out = _apply_smart_filters(arts)
    assert len(out) == 1
    assert out[0]["title"] == "Long enough"


def test_quality_filter_disabled_when_zero(fake_settings):
    _set(fake_settings, "quality_threshold", 0)
    arts = _articles(("A", "tiny"), ("B", "tiny"))
    out = _apply_smart_filters(arts)
    assert len(out) == 2


def test_topic_filter_keeps_matching(fake_settings):
    _set(fake_settings, "topics", ["metro", "tashkent"])
    _set(fake_settings, "quality_threshold", 0)
    arts = _articles(
        ("Metro line opens", "details about new line"),
        ("Random news", "no matching keyword here"),
        ("Bigger news in Tashkent", "context body"),
    )
    out = _apply_smart_filters(arts)
    titles = [a["title"] for a in out]
    assert "Metro line opens" in titles
    assert "Bigger news in Tashkent" in titles
    assert "Random news" not in titles


def test_topic_filter_disabled_when_empty(fake_settings):
    _set(fake_settings, "topics", [])
    _set(fake_settings, "quality_threshold", 0)
    arts = _articles(("A", "x"), ("B", "y"))
    out = _apply_smart_filters(arts)
    assert len(out) == 2


def test_duplicate_filter_collapses_near_identical_titles(fake_settings):
    _set(fake_settings, "topics", [])
    _set(fake_settings, "quality_threshold", 0)
    _set(fake_settings, "dup_threshold", 85)
    arts = _articles(
        ("New metro line opens in Tashkent", "body 1"),
        ("Tashkent opens new metro line today", "body 2"),
        ("Economy update Q1", "body 3"),
    )
    out = _apply_smart_filters(arts)
    # The two metro headlines should collapse to one; economy survives
    assert len(out) == 2


def test_duplicate_filter_disabled_at_100(fake_settings):
    _set(fake_settings, "topics", [])
    _set(fake_settings, "quality_threshold", 0)
    _set(fake_settings, "dup_threshold", 100)
    arts = _articles(
        ("Same title", "a"),
        ("Same title", "b"),
    )
    out = _apply_smart_filters(arts)
    assert len(out) == 2  # disabled, both kept


def test_filters_applied_in_order(fake_settings):
    """Quality runs before topics runs before dedup."""
    _set(fake_settings, "quality_threshold", 50)
    _set(fake_settings, "topics", ["metro"])
    _set(fake_settings, "dup_threshold", 85)
    arts = _articles(
        ("Metro news A", "x" * 100),
        ("Metro news A copy", "x" * 100),
        ("Metro short", "x" * 10),       # dropped by quality
        ("Economy long", "x" * 100),     # dropped by topic
    )
    out = _apply_smart_filters(arts)
    titles = [a["title"] for a in out]
    # After all three: only one metro survives (other dropped by quality
    # / topic / dup), economy gone
    assert len(out) == 1
    assert "Metro news A" in titles
