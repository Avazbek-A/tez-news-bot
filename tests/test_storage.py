"""Tests for the SQLite-backed storage layer (Phase 5).

Each test gets a fresh in-memory-ish DB by pointing SPOT_DB_PATH at a
tmp file and resetting module-level connection / cache state.
"""

from __future__ import annotations

import pytest

from spot_bot.storage import article_cache, db, favorites, filters, op_log, user_settings


@pytest.fixture
async def fresh_db(tmp_path, monkeypatch):
    """Provide a clean DB for each test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    # Reset global connection + caches.
    monkeypatch.setattr(db, "_conn", None)
    monkeypatch.setattr(user_settings, "_cache", {})
    monkeypatch.setattr(user_settings, "_MIGRATED", True)  # skip JSON migration
    await db.connect()
    yield
    await db.close()


# ---------------------------------------------------------------------------
# Migrations + bootstrap
# ---------------------------------------------------------------------------


async def test_migrations_applied(fresh_db):
    rows = await db.fetchall("SELECT version FROM migrations")
    assert {r["version"] for r in rows} == {1}


async def test_tables_exist(fresh_db):
    expected = {"users", "article_cache", "keyword_filters", "favorites", "operation_log"}
    rows = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    present = {r["name"] for r in rows}
    assert expected.issubset(present)


# ---------------------------------------------------------------------------
# user_settings
# ---------------------------------------------------------------------------


async def test_new_user_gets_defaults(fresh_db):
    s = await user_settings.get_all(42)
    assert s["lang"] == "en"
    assert s["voice"].startswith("ru-RU")  # default Dmitry


async def test_set_and_get_scoped_to_user(fresh_db):
    await user_settings.set_value(1, "voice", "en-US-AndrewNeural")
    await user_settings.set_value(2, "voice", "en-US-EmmaNeural")
    assert await user_settings.get(1, "voice") == "en-US-AndrewNeural"
    assert await user_settings.get(2, "voice") == "en-US-EmmaNeural"


async def test_reject_unknown_setting_key(fresh_db):
    with pytest.raises(KeyError):
        await user_settings.set_value(1, "not_a_real_key", "x")


async def test_auto_scrape_round_trips_as_dict(fresh_db):
    cfg = {"enabled": True, "interval_days": 7, "count": 42, "chat_id": 9}
    await user_settings.set_value(1, "auto_scrape", cfg)
    got = await user_settings.get(1, "auto_scrape")
    assert got == cfg


async def test_list_users_with_auto_scrape(fresh_db):
    await user_settings.set_value(
        1, "auto_scrape",
        {"enabled": True, "interval_days": 3, "chat_id": 1},
    )
    await user_settings.set_value(
        2, "auto_scrape",
        {"enabled": False, "interval_days": 3, "chat_id": 2},
    )
    await user_settings.set_value(3, "voice", "emma")  # no auto_scrape
    users = await user_settings.list_users_with_auto_scrape()
    assert {u["user_id"] for u in users} == {1}


# ---------------------------------------------------------------------------
# article_cache
# ---------------------------------------------------------------------------


async def test_cache_miss_returns_none(fresh_db):
    assert await article_cache.lookup("https://x/none") is None


async def test_cache_hit_after_store(fresh_db):
    await article_cache.store(
        "https://spot.uz/a", "Title", "Body", [{"url": "https://x/i.jpg"}],
    )
    hit = await article_cache.lookup("https://spot.uz/a")
    assert hit is not None
    assert hit["title"] == "Title"
    assert hit["body"] == "Body"
    assert hit["images"] == [{"url": "https://x/i.jpg"}]


async def test_empty_body_not_cached(fresh_db):
    await article_cache.store("https://spot.uz/b", "T", "", [])
    assert await article_cache.lookup("https://spot.uz/b") is None


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------


async def test_filter_add_and_list(fresh_db):
    await filters.add(1, "экономика", filters.MODE_INCLUDE)
    await filters.add(1, "спам", filters.MODE_EXCLUDE)
    rules = await filters.list_for(1)
    assert {(r["keyword"], r["mode"]) for r in rules} == {
        ("экономика", "include"),
        ("спам", "exclude"),
    }


async def test_filter_duplicate_add_is_idempotent(fresh_db):
    await filters.add(1, "tech", filters.MODE_INCLUDE)
    await filters.add(1, "tech", filters.MODE_INCLUDE)
    assert len(await filters.list_for(1)) == 1


async def test_filter_remove(fresh_db):
    await filters.add(1, "x", filters.MODE_INCLUDE)
    await filters.add(1, "x", filters.MODE_EXCLUDE)
    # removing without a mode drops both
    deleted = await filters.remove(1, "x")
    assert deleted == 2


async def test_apply_filters_include_required(fresh_db):
    include, exclude = {"tech"}, set()
    articles = [
        {"title": "Tech news", "body": "tech article"},
        {"title": "Economy", "body": "about money"},
    ]
    kept, dropped = filters.apply_filters(articles, include, exclude)
    assert len(kept) == 1
    assert len(dropped) == 1


async def test_apply_filters_exclude_wins(fresh_db):
    include, exclude = {"tech"}, {"spam"}
    articles = [
        {"title": "Tech", "body": "tech spam"},   # exclude wins
        {"title": "Tech", "body": "clean tech"},  # kept
    ]
    kept, _ = filters.apply_filters(articles, include, exclude)
    assert len(kept) == 1
    assert "clean" in kept[0]["body"]


async def test_filters_case_insensitive(fresh_db):
    kept, _ = filters.apply_filters(
        [{"title": "ECONOMY", "body": ""}],
        {"economy"}, set(),
    )
    assert len(kept) == 1


# ---------------------------------------------------------------------------
# favorites
# ---------------------------------------------------------------------------


async def test_favorite_add_and_exists(fresh_db):
    await favorites.add(1, "spotuz/100", "Title", "Body")
    assert await favorites.exists(1, "spotuz/100")
    assert not await favorites.exists(2, "spotuz/100")


async def test_favorite_remove(fresh_db):
    await favorites.add(1, "spotuz/100", "t", "b")
    assert await favorites.remove(1, "spotuz/100")
    assert not await favorites.exists(1, "spotuz/100")


async def test_favorites_list_scoped_per_user(fresh_db):
    await favorites.add(1, "spotuz/1", "A", "a")
    await favorites.add(1, "spotuz/2", "B", "b")
    await favorites.add(2, "spotuz/3", "C", "c")
    mine = await favorites.list_for(1)
    assert {f["post_id"] for f in mine} == {"spotuz/1", "spotuz/2"}


async def test_favorites_truncate_preview(fresh_db):
    long_body = "x" * 1000
    await favorites.add(1, "spotuz/1", "t", long_body)
    row = (await favorites.list_for(1))[0]
    assert len(row["preview"]) < len(long_body)


# ---------------------------------------------------------------------------
# op_log
# ---------------------------------------------------------------------------


async def test_oplog_full_lifecycle(fresh_db):
    await op_log.start("op1", 1, "scrape", {"count": 10})
    await op_log.complete("op1", 9)
    recent = await op_log.recent(1)
    assert recent[0]["status"] == "ok"
    assert recent[0]["article_count"] == 9


async def test_oplog_failure(fresh_db):
    await op_log.start("op2", 1, "scrape")
    await op_log.fail("op2", "NetworkError: dns")
    recent = await op_log.recent(1)
    assert recent[0]["status"] == "failed"
    assert "NetworkError" in recent[0]["error"]


async def test_oplog_scoped_to_user(fresh_db):
    await op_log.start("a", 1, "scrape")
    await op_log.start("b", 2, "scrape")
    r1 = await op_log.recent(1)
    r2 = await op_log.recent(2)
    assert {r["op_id"] for r in r1} == {"a"}
    assert {r["op_id"] for r in r2} == {"b"}
