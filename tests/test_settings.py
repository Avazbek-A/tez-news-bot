"""Tests for settings persistence: atomic writes, cache, defaults."""

import json

import pytest

from spot_bot import settings


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    """Redirect settings file to a tmp path and reset cache between tests."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    settings.invalidate_cache()
    yield path
    settings.invalidate_cache()


def test_defaults_when_file_missing(tmp_settings):
    loaded = settings.load_settings()
    assert loaded["voice"] == settings._DEFAULTS["voice"]
    assert loaded["language"] == settings._DEFAULTS["language"]


def test_corrupt_json_falls_back_to_defaults(tmp_settings):
    tmp_settings.write_text("{not valid json")
    loaded = settings.load_settings()
    assert loaded["voice"] == settings._DEFAULTS["voice"]


def test_new_defaults_merged_into_existing_file(tmp_settings):
    # Simulate an older settings file missing a newly-added key.
    tmp_settings.write_text(json.dumps({"voice": "custom"}))
    loaded = settings.load_settings()
    assert loaded["voice"] == "custom"
    assert loaded["language"] == settings._DEFAULTS["language"]  # default filled in


def test_set_and_get_roundtrip(tmp_settings):
    settings.set_setting("voice", "andrew")
    assert settings.get_setting("voice") == "andrew"
    # Written to disk
    saved = json.loads(tmp_settings.read_text())
    assert saved["voice"] == "andrew"


def test_cache_avoids_disk_reads(tmp_settings, monkeypatch):
    settings.load_settings()  # populate cache
    read_calls = {"n": 0}
    original = settings._read_from_disk

    def counting_read():
        read_calls["n"] += 1
        return original()

    monkeypatch.setattr(settings, "_read_from_disk", counting_read)
    # Many reads, zero disk hits
    for _ in range(10):
        settings.load_settings()
    assert read_calls["n"] == 0


def test_save_updates_cache(tmp_settings):
    settings.load_settings()  # populate cache
    settings.set_setting("voice", "emma")
    # Even if we re-invalidate, disk should have the new value
    settings.invalidate_cache()
    assert settings.get_setting("voice") == "emma"


def test_load_returns_independent_copy(tmp_settings):
    """Mutating the returned dict must not poison the cache."""
    a = settings.load_settings()
    a["voice"] = "MUTATED"
    b = settings.load_settings()
    assert b["voice"] != "MUTATED"
