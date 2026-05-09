"""Tests for settings persistence + the legacy channel_url → sources migration.

Existing user_settings.json files (pre-Phase 5) only have channel_url.
get_sources() must auto-migrate without losing the existing channel.
"""
import json

from spot_bot import settings as s


def test_migration_from_channel_url_only(temp_settings_path):
    # Simulate a legacy file with only channel_url
    temp_settings_path.write_text(json.dumps({
        "channel_url": "https://t.me/s/spotuz",
    }))
    sources = s.get_sources()
    assert len(sources) == 1
    assert sources[0]["type"] == "telegram"
    assert sources[0]["url"] == "https://t.me/s/spotuz"
    assert sources[0]["id"] == "default"


def test_no_migration_when_sources_already_present(temp_settings_path):
    pre = [{"id": "spotuz", "type": "telegram",
            "url": "https://t.me/s/spotuz", "label": "Spot"}]
    temp_settings_path.write_text(json.dumps({
        "channel_url": "https://t.me/s/something_else",
        "sources": pre,
    }))
    sources = s.get_sources()
    assert sources == pre


def test_add_source_replaces_existing_id(temp_settings_path):
    s.add_source({"id": "x", "type": "telegram", "url": "u1", "label": "First"})
    s.add_source({"id": "x", "type": "rss", "url": "u2", "label": "Replaced"})
    sources = s.get_sources()
    matching = [src for src in sources if src["id"] == "x"]
    assert len(matching) == 1
    assert matching[0]["url"] == "u2"


def test_remove_source_by_id(temp_settings_path):
    s.add_source({"id": "a", "type": "rss", "url": "u", "label": "A"})
    s.add_source({"id": "b", "type": "rss", "url": "u", "label": "B"})
    assert s.remove_source("a") is True
    assert s.remove_source("nope") is False
    remaining = [src["id"] for src in s.get_sources()]
    assert "a" not in remaining
    assert "b" in remaining


def test_remember_delivered_caps_at_max(temp_settings_path):
    # Fewer than max — all kept
    s.remember_delivered([1, 2, 3, 4, 5])
    assert sorted(s.get_setting("delivered_post_ids")) == [1, 2, 3, 4, 5]


def test_remember_delivered_dedupes(temp_settings_path):
    s.remember_delivered([10, 11])
    s.remember_delivered([11, 12])
    ids = sorted(s.get_setting("delivered_post_ids"))
    assert ids == [10, 11, 12]


def test_add_remove_bookmark(temp_settings_path):
    s.add_bookmark(35808)
    s.add_bookmark(35808)  # idempotent
    s.add_bookmark(35900)
    ids = sorted(int(b["id"]) for b in s.get_bookmarks())
    assert ids == [35808, 35900]
    assert s.remove_bookmark(35808) is True
    assert s.remove_bookmark(99999) is False
    remaining = [int(b["id"]) for b in s.get_bookmarks()]
    assert remaining == [35900]


def test_bookmark_tags_added_and_merged(temp_settings_path):
    s.add_bookmark(100, tags=["economy"])
    s.add_bookmark(100, tags=["interviews"])  # merges
    items = s.get_bookmarks()
    assert len(items) == 1
    assert sorted(items[0]["tags"]) == ["economy", "interviews"]


def test_legacy_bookmark_format_migrates(temp_settings_path):
    """Old format: bookmarked_post_ids = [int]. New: bookmarks = [{id, tags}]."""
    import json
    temp_settings_path.write_text(json.dumps({
        "bookmarked_post_ids": [35808, 35809],
    }))
    items = s.get_bookmarks()
    assert sorted(int(b["id"]) for b in items) == [35808, 35809]
    for b in items:
        assert b["tags"] == []
