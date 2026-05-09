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
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


DB_PATH = Path(__file__).parent / "history.db"


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
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(_SCHEMA)
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
