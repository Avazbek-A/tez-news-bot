"""Tests for the SQLite delivery-history layer."""
import tempfile
from pathlib import Path

import pytest

from spot_bot import history_db


@pytest.fixture
def temp_db(monkeypatch):
    tmp = Path(tempfile.mkdtemp()) / "history.db"
    monkeypatch.setattr(history_db, "DB_PATH", tmp)
    yield tmp


def test_record_and_find_returns_match(temp_db):
    articles = [
        {
            "id": "spotuz/35808",
            "title": "Tashkent metro extension opens",
            "body": "The new line connects three districts...",
            "date": "2026-05-08",
        },
        {
            "id": "spotuz/35809",
            "title": "Economy update: GDP growth",
            "body": "Q1 growth came in at 6.2 percent.",
            "date": "2026-05-09",
        },
    ]
    history_db.record_articles(articles)

    matches = history_db.find("metro")
    assert len(matches) == 1
    assert matches[0]["title"].startswith("Tashkent metro")
    assert matches[0]["post_id"] == 35808


def test_find_searches_body_head_too(temp_db):
    history_db.record_articles([{
        "id": "spotuz/100",
        "title": "Random title",
        "body": "Mentions tashkent metro inside the body though.",
        "date": "2026-05-08",
    }])
    matches = history_db.find("metro")
    assert len(matches) == 1


def test_find_returns_empty_for_no_match(temp_db):
    history_db.record_articles([{
        "id": "spotuz/1", "title": "Foo", "body": "Bar", "date": "2026-01-01"
    }])
    assert history_db.find("xyz_unmatched_query") == []


def test_record_is_idempotent(temp_db):
    article = {"id": "spotuz/100", "title": "Once",
               "body": "First version body", "date": "2026-05-08"}
    history_db.record_articles([article])
    history_db.record_articles([article])  # second time
    assert len(history_db.find("Once")) == 1


def test_record_upserts_changed_title(temp_db):
    history_db.record_articles([{
        "id": "spotuz/100", "title": "Old title",
        "body": "Body", "date": "2026-01-01",
    }])
    history_db.record_articles([{
        "id": "spotuz/100", "title": "New title",
        "body": "Body", "date": "2026-01-01",
    }])
    matches = history_db.find("New title")
    assert len(matches) == 1
    assert matches[0]["title"] == "New title"


def test_summary_cache_roundtrip(temp_db):
    history_db.record_articles([{
        "id": "spotuz/200", "title": "X", "body": "Y", "date": "2026-01-01",
    }])
    assert history_db.get_cached_summary("spotuz/200") is None
    history_db.cache_summary("spotuz/200", "Quick summary text", "en")
    cached = history_db.get_cached_summary("spotuz/200")
    assert cached == ("Quick summary text", "en")


def test_stats_counts_and_total_audio(temp_db):
    history_db.record_articles([
        {"id": "spotuz/1", "title": "a", "body": "b", "date": "2026-01-01"},
        {"id": "spotuz/2", "title": "c", "body": "d", "date": "2026-01-02"},
    ])
    history_db.update_audio_duration("spotuz/1", 120.0)
    history_db.update_audio_duration("spotuz/2", 30.0)
    s = history_db.stats(since_unix=0)
    assert s["n_articles"] == 2
    assert s["total_audio_sec"] == 150.0


def test_split_article_id():
    assert history_db._split_article_id("spotuz/35808") == ("spotuz", 35808)
    assert history_db._split_article_id("default/100") == ("default", 100)
    assert history_db._split_article_id("noslash") == ("noslash", None)
    assert history_db._split_article_id("") == ("unknown", None)


def test_translation_cache_roundtrip(temp_db):
    history_db.cache_translation(
        "spotuz/100", "de",
        title="Tashkent Metro öffnet neue Linie",
        body="Eine neue U-Bahn-Linie wurde heute eröffnet.",
    )
    got = history_db.get_cached_translation("spotuz/100", "de")
    assert got is not None
    title, body = got
    assert "Metro" in title
    assert "U-Bahn" in body


def test_translation_cache_separate_per_lang(temp_db):
    history_db.cache_translation("spotuz/200", "de", "Titel-DE", "Körper-DE")
    history_db.cache_translation("spotuz/200", "tr", "Başlık-TR", "Gövde-TR")
    de = history_db.get_cached_translation("spotuz/200", "de")
    tr = history_db.get_cached_translation("spotuz/200", "tr")
    assert de == ("Titel-DE", "Körper-DE")
    assert tr == ("Başlık-TR", "Gövde-TR")


def test_translation_cache_upserts(temp_db):
    history_db.cache_translation("spotuz/300", "de", "v1 title", "v1 body")
    history_db.cache_translation("spotuz/300", "de", "v2 title", "v2 body")
    got = history_db.get_cached_translation("spotuz/300", "de")
    assert got == ("v2 title", "v2 body")


def test_translation_cache_miss_returns_none(temp_db):
    assert history_db.get_cached_translation("missing/article", "de") is None
    assert history_db.get_cached_translation("", "de") is None
