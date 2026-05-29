"""Tests for the SQLite migration runner + settings versioning."""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def hdb(tmp_path, monkeypatch):
    import spot_bot.history_db as h
    monkeypatch.setattr(h, "DB_PATH", tmp_path / "m.db")
    return h


def _user_version(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


def test_fresh_db_stamped_to_current_version(hdb):
    # Touch the DB so it's created + migrated.
    hdb.metrics_snapshot(days=7)
    assert _user_version(hdb.DB_PATH) == hdb._SCHEMA_VERSION


def test_pending_migration_applied(hdb, monkeypatch):
    """A registered migration > current version runs and bumps the marker."""
    # Pretend we're shipping a v2 that adds a column.
    monkeypatch.setattr(hdb, "_SCHEMA_VERSION", 2)
    monkeypatch.setattr(hdb, "_MIGRATIONS", {
        2: ["ALTER TABLE history ADD COLUMN smoke_col TEXT DEFAULT ''"],
    })
    # First connect creates v1 tables, stamps v1, then applies migration 2.
    hdb.metrics_snapshot(days=7)
    assert _user_version(hdb.DB_PATH) == 2
    # The new column exists.
    conn = sqlite3.connect(hdb.DB_PATH)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(history)")]
    finally:
        conn.close()
    assert "smoke_col" in cols


def test_migration_is_idempotent(hdb, monkeypatch):
    monkeypatch.setattr(hdb, "_SCHEMA_VERSION", 2)
    monkeypatch.setattr(hdb, "_MIGRATIONS", {
        2: ["ALTER TABLE history ADD COLUMN smoke_col TEXT DEFAULT ''"],
    })
    hdb.metrics_snapshot(days=7)   # applies migration
    # Second connect must NOT re-run the ALTER (would raise duplicate column).
    hdb.metrics_snapshot(days=7)
    assert _user_version(hdb.DB_PATH) == 2


# ---------- settings versioning ----------

def test_settings_stamped_with_version(tmp_path, monkeypatch):
    from spot_bot import settings as s
    monkeypatch.setattr(s, "SETTINGS_PATH", tmp_path / "settings.json")
    loaded = s.load_settings()
    assert loaded["settings_version"] == s._SETTINGS_VERSION


def test_migrate_settings_noop_when_current():
    from spot_bot import settings as s
    data = {"settings_version": s._SETTINGS_VERSION, "voice": "x"}
    out = s._migrate_settings(dict(data))
    assert out["settings_version"] == s._SETTINGS_VERSION
    assert out["voice"] == "x"
