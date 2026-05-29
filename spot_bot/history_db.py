"""SQLite-backed delivery history.

Used by:
- /find <query>: case-insensitive search across delivered article titles + body heads.
- Phase 8 (LLM summaries): cached summary + summary_lang columns.
- Phase 9 (/stats): article counts and total audio duration.

The database lives at spot_bot/history.db. We use a small synthetic
schema and plain LIKE queries — FTS5 would be overkill for a personal
bot's volume.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Iterable, Optional

from spot_bot.paths import data_path, ensure_parent

logger = logging.getLogger(__name__)


# Lives on DATA_DIR (a mounted volume in prod), else next to the code.
DB_PATH = data_path("history.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    article_id  TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    post_id     INTEGER NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    body_head   TEXT NOT NULL DEFAULT '',
    date_iso    TEXT NOT NULL DEFAULT '',
    delivered_at INTEGER NOT NULL,
    audio_duration_sec REAL DEFAULT 0,
    summary     TEXT,
    summary_lang TEXT
);
CREATE INDEX IF NOT EXISTS idx_post_id ON history(post_id);
CREATE INDEX IF NOT EXISTS idx_date    ON history(date_iso);
CREATE INDEX IF NOT EXISTS idx_source  ON history(source_id);

-- Translation cache: one row per (article, target_lang) pair.
CREATE TABLE IF NOT EXISTS translations (
    article_id TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    body  TEXT NOT NULL,
    cached_at INTEGER NOT NULL,
    PRIMARY KEY (article_id, target_lang)
);

-- Operational metrics: one tiny row per scrape run. No external system —
-- lives in this same SQLite file, so it travels with the bot when hosting
-- moves (e.g. Railway -> a Linux laptop). Read via /metrics.
CREATE TABLE IF NOT EXISTS metrics_runs (
    ts           INTEGER NOT NULL,         -- unix time at run completion
    articles     INTEGER NOT NULL DEFAULT 0,
    skipped_seen INTEGER NOT NULL DEFAULT 0,
    muted        INTEGER NOT NULL DEFAULT 0,
    audio        INTEGER NOT NULL DEFAULT 0,
    images       INTEGER NOT NULL DEFAULT 0,
    partial      INTEGER NOT NULL DEFAULT 0, -- 0/1
    duration_ms  INTEGER NOT NULL DEFAULT 0,
    ok           INTEGER NOT NULL DEFAULT 1, -- 0 = run errored
    error        TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics_runs(ts);
"""


# ---------------------------------------------------------------------------
# Schema versioning / migrations
#
# `_SCHEMA` above is the v1 baseline — it creates a fresh DB's tables and
# must NOT be changed again. Every subsequent schema change (new column,
# new table, backfill) goes in `_MIGRATIONS` as the NEXT integer version,
# and `_migrate` applies the pending ones in order, tracked by SQLite's
# built-in `PRAGMA user_version`. This makes column changes safe in
# production instead of relying on CREATE-IF-NOT-EXISTS guesswork.
#
# Example of a future migration:
#   _MIGRATIONS = {
#       2: ["ALTER TABLE history ADD COLUMN lang TEXT DEFAULT ''"],
#   }
# ---------------------------------------------------------------------------
_SCHEMA_VERSION = 1
_MIGRATIONS: dict[int, list[str]] = {}


def _migrate(conn) -> None:
    """Bring the DB schema up to _SCHEMA_VERSION via user_version steps."""
    cur_v = conn.execute("PRAGMA user_version").fetchone()[0]
    if cur_v == 0:
        # Fresh DB or a pre-versioning one. Either way `_SCHEMA` (run on
        # connect) has created the v1 baseline tables, so stamp it as v1 —
        # then let the loop below apply any migrations (2+) on top.
        conn.execute("PRAGMA user_version = 1")
        cur_v = 1
    for version in sorted(_MIGRATIONS):
        if version > cur_v:
            for stmt in _MIGRATIONS[version]:
                conn.execute(stmt)
            conn.execute(f"PRAGMA user_version = {version}")
            cur_v = version


def _connect():
    ensure_parent(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _split_article_id(article_id: str):
    """Split 'spotuz/35808' -> ('spotuz', 35808). Returns (source_id, None)
    on parse failure."""
    if not article_id:
        return ("unknown", None)
    if "/" not in article_id:
        return (article_id, None)
    source_id, raw = article_id.rsplit("/", 1)
    try:
        return (source_id, int(raw))
    except ValueError:
        return (source_id, None)


def record_articles(articles: Iterable[dict]) -> int:
    """Insert (or upsert) a batch of articles into the history table.
    Returns the number of rows affected.
    """
    rows: list[tuple] = []
    now = int(time.time())
    for a in articles:
        article_id = a.get("id", "")
        if not article_id:
            continue
        source_id, post_id = _split_article_id(article_id)
        title = (a.get("title") or "").strip()
        body = (a.get("body") or "")
        body_head = body[:500].strip()
        date_iso = (a.get("date") or "").strip()
        rows.append((
            article_id, source_id, post_id or 0,
            title, body_head, date_iso, now,
        ))
    if not rows:
        return 0
    try:
        conn = _connect()
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO history (
                        article_id, source_id, post_id, title,
                        body_head, date_iso, delivered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(article_id) DO UPDATE SET
                        title=excluded.title,
                        body_head=excluded.body_head,
                        date_iso=excluded.date_iso,
                        delivered_at=excluded.delivered_at
                    """,
                    rows,
                )
        finally:
            conn.close()
        return len(rows)
    except sqlite3.Error as e:
        logger.warning("history_db record_articles failed: %s", e)
        return 0


def find(query: str, limit: int = 20):
    """Case-insensitive substring search across title + body_head.
    Returns list of dicts, most-recent (delivered_at desc) first."""
    if not query or not query.strip():
        return []
    pattern = f"%{query.strip()}%"
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                SELECT article_id, source_id, post_id, title, body_head,
                       date_iso, delivered_at, summary
                FROM history
                WHERE title LIKE ? OR body_head LIKE ?
                ORDER BY delivered_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db find failed: %s", e)
        return []


def update_audio_duration(article_id: str, seconds: float) -> None:
    if not article_id or seconds <= 0:
        return
    try:
        conn = _connect()
        try:
            with conn:
                conn.execute(
                    "UPDATE history SET audio_duration_sec = ? "
                    "WHERE article_id = ?",
                    (float(seconds), article_id),
                )
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db update_audio_duration failed: %s", e)


def get_cached_summary(article_id: str) -> Optional[tuple[str, str]]:
    """Return (summary, lang) if cached, or None."""
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                "SELECT summary, summary_lang FROM history WHERE article_id = ?",
                (article_id,),
            )
            row = cur.fetchone()
            if row and row["summary"]:
                return (row["summary"], row["summary_lang"] or "")
            return None
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db get_cached_summary failed: %s", e)
        return None


def cache_translation(article_id: str, target_lang: str,
                      title: str, body: str) -> None:
    """Store a translation. Upserts on (article_id, target_lang)."""
    if not article_id or not target_lang or not body:
        return
    try:
        conn = _connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO translations (
                        article_id, target_lang, title, body, cached_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(article_id, target_lang) DO UPDATE SET
                        title=excluded.title,
                        body=excluded.body,
                        cached_at=excluded.cached_at
                    """,
                    (article_id, target_lang, title or "", body, int(time.time())),
                )
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db cache_translation failed: %s", e)


def get_cached_translation(article_id: str, target_lang: str):
    """Return (title, body) tuple if cached for this language, else None."""
    if not article_id or not target_lang:
        return None
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                "SELECT title, body FROM translations "
                "WHERE article_id = ? AND target_lang = ?",
                (article_id, target_lang),
            )
            row = cur.fetchone()
            if row:
                return (row["title"] or "", row["body"])
            return None
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db get_cached_translation failed: %s", e)
        return None


def cache_summary(article_id: str, summary: str, lang: str) -> None:
    if not article_id or not summary:
        return
    try:
        conn = _connect()
        try:
            with conn:
                conn.execute(
                    "UPDATE history SET summary = ?, summary_lang = ? "
                    "WHERE article_id = ?",
                    (summary, lang, article_id),
                )
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db cache_summary failed: %s", e)


def record_run(*, articles=0, skipped_seen=0, muted=0, audio=0, images=0,
               partial=False, duration_ms=0, ok=True, error=None) -> None:
    """Record one scrape run's operational metrics. Best-effort — never
    raises, so a metrics failure can't break a delivery."""
    try:
        conn = _connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO metrics_runs (
                        ts, articles, skipped_seen, muted, audio, images,
                        partial, duration_ms, ok, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(time.time()), int(articles), int(skipped_seen),
                        int(muted), int(audio), int(images),
                        1 if partial else 0, int(duration_ms),
                        1 if ok else 0, (error or None),
                    ),
                )
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db record_run failed: %s", e)


def metrics_snapshot(days: int = 7) -> dict:
    """Aggregate recent run metrics over the last `days` (and today).

    Returns counts/sums plus derived rates — everything /metrics needs to
    show bot health without any external monitoring system.
    """
    now = int(time.time())
    since_week = now - days * 86400
    since_today = now - 86400
    empty = {
        "runs": 0, "articles": 0, "skipped_seen": 0, "muted": 0,
        "audio": 0, "images": 0, "partial": 0, "errors": 0,
        "avg_duration_ms": 0, "today_runs": 0, "today_articles": 0,
        "days": days,
    }
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                SELECT COUNT(*) AS runs,
                       COALESCE(SUM(articles), 0) AS articles,
                       COALESCE(SUM(skipped_seen), 0) AS skipped_seen,
                       COALESCE(SUM(muted), 0) AS muted,
                       COALESCE(SUM(audio), 0) AS audio,
                       COALESCE(SUM(images), 0) AS images,
                       COALESCE(SUM(partial), 0) AS partial,
                       COALESCE(SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END), 0) AS errors,
                       COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
                FROM metrics_runs WHERE ts >= ?
                """,
                (since_week,),
            )
            row = cur.fetchone()
            cur2 = conn.execute(
                "SELECT COUNT(*) AS r, COALESCE(SUM(articles),0) AS a "
                "FROM metrics_runs WHERE ts >= ?",
                (since_today,),
            )
            today = cur2.fetchone()
            return {
                "runs": int(row["runs"] or 0),
                "articles": int(row["articles"] or 0),
                "skipped_seen": int(row["skipped_seen"] or 0),
                "muted": int(row["muted"] or 0),
                "audio": int(row["audio"] or 0),
                "images": int(row["images"] or 0),
                "partial": int(row["partial"] or 0),
                "errors": int(row["errors"] or 0),
                "avg_duration_ms": int(row["avg_duration_ms"] or 0),
                "today_runs": int(today["r"] or 0),
                "today_articles": int(today["a"] or 0),
                "days": days,
            }
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db metrics_snapshot failed: %s", e)
        return empty


def stats(since_unix: int = 0) -> dict:
    """Return rough counts + total audio duration for /stats.
    `since_unix` filters by delivered_at >= since_unix; pass 0 for all-time."""
    try:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                SELECT COUNT(*) AS n_articles,
                       COALESCE(SUM(audio_duration_sec), 0) AS total_audio,
                       MIN(delivered_at) AS first_delivery
                FROM history
                WHERE delivered_at >= ?
                """,
                (since_unix,),
            )
            row = cur.fetchone()
            if row is None:
                return {"n_articles": 0, "total_audio_sec": 0.0, "first_delivery": 0}
            return {
                "n_articles": int(row["n_articles"] or 0),
                "total_audio_sec": float(row["total_audio"] or 0.0),
                "first_delivery": int(row["first_delivery"] or 0),
            }
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("history_db stats failed: %s", e)
        return {"n_articles": 0, "total_audio_sec": 0.0, "first_delivery": 0}
