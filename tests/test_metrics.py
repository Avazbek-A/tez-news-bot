"""Tests for the self-contained SQLite metrics (history_db.record_run /
metrics_snapshot).

No external monitoring system: metrics live in the same SQLite file as
history, so they travel with the bot to any host. Tests point DB_PATH at
a temp file so they don't touch the real db.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def hdb(tmp_path, monkeypatch):
    """Fresh history_db pointed at a temp DB file."""
    import spot_bot.history_db as h
    monkeypatch.setattr(h, "DB_PATH", tmp_path / "test_history.db")
    return h


def test_record_run_and_snapshot_basic(hdb):
    hdb.record_run(articles=5, skipped_seen=2, muted=1, audio=3, images=4,
                   partial=False, duration_ms=1200, ok=True)
    hdb.record_run(articles=3, skipped_seen=0, muted=0, audio=0, images=0,
                   partial=True, duration_ms=800, ok=True)
    m = hdb.metrics_snapshot(days=7)
    assert m["runs"] == 2
    assert m["articles"] == 8
    assert m["skipped_seen"] == 2
    assert m["muted"] == 1
    assert m["audio"] == 3
    assert m["images"] == 4
    assert m["partial"] == 1
    assert m["errors"] == 0
    assert m["avg_duration_ms"] == 1000  # (1200 + 800) / 2


def test_record_run_counts_errors(hdb):
    hdb.record_run(articles=1, ok=True, duration_ms=100)
    hdb.record_run(articles=0, ok=False, error="boom", duration_ms=50)
    m = hdb.metrics_snapshot(days=7)
    assert m["runs"] == 2
    assert m["errors"] == 1


def test_snapshot_empty_db(hdb):
    m = hdb.metrics_snapshot(days=7)
    assert m["runs"] == 0
    assert m["articles"] == 0
    assert m["errors"] == 0
    assert m["avg_duration_ms"] == 0


def test_snapshot_window_excludes_old_runs(hdb, monkeypatch):
    """Runs older than the window aren't counted."""
    import time as _time
    # Record one run "8 days ago" by monkeypatching time.time inside the
    # record call.
    real_time = _time.time
    monkeypatch.setattr(hdb.time, "time", lambda: real_time() - 8 * 86400)
    hdb.record_run(articles=99, ok=True)
    # Restore time and record a fresh run.
    monkeypatch.setattr(hdb.time, "time", real_time)
    hdb.record_run(articles=1, ok=True)

    m = hdb.metrics_snapshot(days=7)
    assert m["runs"] == 1          # only the fresh one
    assert m["articles"] == 1


def test_record_run_never_raises_on_bad_db(monkeypatch, tmp_path):
    """A metrics failure must never break a delivery — best-effort only."""
    import spot_bot.history_db as h
    # Point at a path that can't be opened (a directory).
    bad = tmp_path / "adir"
    bad.mkdir()
    monkeypatch.setattr(h, "DB_PATH", bad)  # opening a dir as sqlite fails
    # Should swallow the error, not raise.
    h.record_run(articles=1, ok=True)
    assert h.metrics_snapshot(days=7)["runs"] == 0


def test_metrics_body_translation_complete():
    """The /metrics template exists in all 5 languages and renders."""
    import os
    os.environ.setdefault("BOT_TOKEN", "test:dummy")
    from spot_bot.translations import _STRINGS, t
    for lang in ("en", "ru", "uz", "de", "tr"):
        assert lang in _STRINGS["metrics_body"], lang
    rendered = t("metrics_body", "en", days=7, runs=2, today_runs=1,
                 today_articles=5, articles=8, audio=3, images=4,
                 skipped_seen=2, muted=1, errors=0, err_pct=0,
                 partial=1, partial_pct=50, avg_s=1.0)
    assert "Health" in rendered
