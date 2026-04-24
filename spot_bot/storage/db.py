"""SQLite connection management + schema migrations.

Uses a single shared aiosqlite connection for the lifetime of the bot.
For our workload (one bot process, modest write volume), a single
connection with `PRAGMA journal_mode=WAL` is simpler than a pool and
plenty fast.

Migrations are forward-only and numbered. Add a new entry to the
`_MIGRATIONS` list to evolve the schema — never mutate existing entries
in production.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "spot_bot.db"
DB_PATH = Path(os.environ.get("SPOT_DB_PATH", str(DEFAULT_DB_PATH)))


# Each migration is (version, sql). The runner applies them in order and
# records the version in the `migrations` table. Safe to add; never edit.
_MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            lang             TEXT,
            voice            TEXT,
            speed            TEXT,
            channel_url      TEXT,
            last_scraped_id  INTEGER,
            auto_scrape_json TEXT,
            created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS article_cache (
            url           TEXT PRIMARY KEY,
            title         TEXT,
            body          TEXT,
            images_json   TEXT,
            source        TEXT,
            fetched_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_article_cache_fetched
            ON article_cache(fetched_at);

        CREATE TABLE IF NOT EXISTS keyword_filters (
            user_id  INTEGER NOT NULL,
            keyword  TEXT NOT NULL,
            mode     TEXT NOT NULL CHECK(mode IN ('include', 'exclude')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, keyword, mode)
        );

        CREATE TABLE IF NOT EXISTS favorites (
            user_id    INTEGER NOT NULL,
            post_id    TEXT NOT NULL,
            title      TEXT,
            body       TEXT,
            saved_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, post_id)
        );
        CREATE INDEX IF NOT EXISTS idx_favorites_user
            ON favorites(user_id, saved_at DESC);

        CREATE TABLE IF NOT EXISTS operation_log (
            op_id         TEXT PRIMARY KEY,
            user_id       INTEGER,
            command       TEXT,
            args_json     TEXT,
            started_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at  TEXT,
            status        TEXT,       -- running / ok / failed / cancelled
            article_count INTEGER,
            error         TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_oplog_user
            ON operation_log(user_id, started_at DESC);
        """,
    ),
]


_conn: aiosqlite.Connection | None = None


async def connect() -> aiosqlite.Connection:
    """Open (once) and return the shared DB connection, applying migrations."""
    global _conn
    if _conn is not None:
        return _conn

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Opening SQLite database at %s", DB_PATH)
    conn = await aiosqlite.connect(str(DB_PATH))
    conn.row_factory = aiosqlite.Row
    # WAL gives better concurrent read/write for a long-running bot.
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await _apply_migrations(conn)
    _conn = conn
    return _conn


async def close() -> None:
    """Close the shared connection. Safe to call multiple times."""
    global _conn
    if _conn is None:
        return
    try:
        await _conn.close()
    finally:
        _conn = None


async def get_conn() -> aiosqlite.Connection:
    """Convenience: lazily connects on first use."""
    return await connect()


async def _apply_migrations(conn: aiosqlite.Connection) -> None:
    # Bootstrap: ensure the migrations table exists before we can query it.
    await conn.executescript(
        "CREATE TABLE IF NOT EXISTS migrations ("
        "version INTEGER PRIMARY KEY, "
        "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    await conn.commit()

    async with conn.execute("SELECT version FROM migrations") as cur:
        rows = await cur.fetchall()
    applied = {r["version"] for r in rows}

    for version, sql in _MIGRATIONS:
        if version in applied:
            continue
        logger.info("Applying migration v%d", version)
        await conn.executescript(sql)
        await conn.execute(
            "INSERT INTO migrations(version) VALUES(?)", (version,),
        )
        await conn.commit()


# ---------------------------------------------------------------------------
# Tiny helpers used by storage submodules
# ---------------------------------------------------------------------------


async def execute(sql: str, params: Iterable[Any] = ()) -> None:
    conn = await get_conn()
    await conn.execute(sql, tuple(params))
    await conn.commit()


async def fetchone(
    sql: str, params: Iterable[Any] = (),
) -> aiosqlite.Row | None:
    conn = await get_conn()
    async with conn.execute(sql, tuple(params)) as cur:
        return await cur.fetchone()


async def fetchall(
    sql: str, params: Iterable[Any] = (),
) -> list[aiosqlite.Row]:
    conn = await get_conn()
    async with conn.execute(sql, tuple(params)) as cur:
        return list(await cur.fetchall())
