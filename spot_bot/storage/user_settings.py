"""Per-user settings stored in SQLite.

The legacy `spot_bot.settings` module kept a single global JSON file.
This module scopes every setting to a Telegram user_id. On first access
for a given user we seed their row from the legacy JSON (if present)
and then defaults, so existing deployments transition cleanly.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from spot_bot.config import CHANNEL_URL, DEFAULT_LANGUAGE, DEFAULT_VOICE, TTS_RATE
from spot_bot.storage import db

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "lang": DEFAULT_LANGUAGE,
    "voice": DEFAULT_VOICE,
    "speed": TTS_RATE,
    "channel_url": CHANNEL_URL,
    "last_scraped_id": None,
    "auto_scrape": None,  # serialized as auto_scrape_json in the DB
}

# Map friendly key names to their DB columns. Keys not in this map are
# rejected — this keeps typos from silently creating useless rows.
_COLUMNS = {
    "lang": "lang",
    "voice": "voice",
    "speed": "speed",
    "channel_url": "channel_url",
    "last_scraped_id": "last_scraped_id",
    "auto_scrape": "auto_scrape_json",
}


# Cache: user_id -> dict of settings. Invalidated on write.
_cache: dict[int, dict[str, Any]] = {}
_cache_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Migration from legacy global JSON
# ---------------------------------------------------------------------------

_MIGRATED = False


async def migrate_legacy_json_if_needed() -> None:
    """If the old `spot_bot/user_settings.json` exists and the DB is empty,
    stash its values as template defaults so any new user inherits them.

    We don't know which user created the JSON settings, so we can't
    attribute them to a specific user. Instead we store them as a
    synthetic row with user_id=0 ("global template"). get_settings()
    falls back to this template when bootstrapping a new user.
    """
    global _MIGRATED
    if _MIGRATED:
        return
    _MIGRATED = True

    legacy_path = Path(__file__).resolve().parents[1] / "user_settings.json"
    if not legacy_path.exists():
        return

    existing = await db.fetchone(
        "SELECT user_id FROM users WHERE user_id = 0",
    )
    if existing is not None:
        return

    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read legacy settings at %s: %s", legacy_path, e)
        return

    logger.info("Seeding global template (user_id=0) from legacy JSON settings")
    await db.execute(
        """
        INSERT INTO users
            (user_id, lang, voice, speed, channel_url, auto_scrape_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            0,
            data.get("language") or DEFAULT_LANGUAGE,
            data.get("voice") or DEFAULT_VOICE,
            data.get("speed") or TTS_RATE,
            data.get("channel_url") or CHANNEL_URL,
            json.dumps(data.get("auto_scrape")) if data.get("auto_scrape") else None,
        ),
    )


async def _template_defaults() -> dict[str, Any]:
    """If a global template row exists (migrated from legacy JSON), use it
    to seed new users; otherwise fall back to the hard-coded defaults."""
    row = await db.fetchone("SELECT * FROM users WHERE user_id = 0")
    if row is None:
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    for key, column in _COLUMNS.items():
        val = row[column]
        if val is None:
            continue
        if key == "auto_scrape":
            try:
                merged[key] = json.loads(val) if val else None
            except json.JSONDecodeError:
                merged[key] = None
        else:
            merged[key] = val
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_all(user_id: int) -> dict[str, Any]:
    """Return a complete settings dict for the user, creating the row
    (from template/defaults) if needed."""
    async with _cache_lock:
        cached = _cache.get(user_id)
    if cached is not None:
        return dict(cached)

    await migrate_legacy_json_if_needed()

    row = await db.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if row is None:
        defaults = await _template_defaults()
        await db.execute(
            """
            INSERT INTO users
                (user_id, lang, voice, speed, channel_url, auto_scrape_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                defaults["lang"], defaults["voice"], defaults["speed"],
                defaults["channel_url"],
                json.dumps(defaults["auto_scrape"]) if defaults["auto_scrape"] else None,
            ),
        )
        settings = defaults
    else:
        settings = {}
        for key, column in _COLUMNS.items():
            val = row[column]
            if key == "auto_scrape":
                settings[key] = json.loads(val) if val else None
            else:
                settings[key] = val if val is not None else _DEFAULTS[key]

    async with _cache_lock:
        _cache[user_id] = dict(settings)
    return dict(settings)


async def get(user_id: int, key: str) -> Any:
    all_ = await get_all(user_id)
    return all_.get(key, _DEFAULTS.get(key))


async def set_value(user_id: int, key: str, value: Any) -> None:
    if key not in _COLUMNS:
        raise KeyError(f"Unknown setting: {key}")
    # Ensure the row exists.
    await get_all(user_id)

    column = _COLUMNS[key]
    stored = json.dumps(value) if key == "auto_scrape" else value
    await db.execute(
        f"""
        UPDATE users
           SET {column} = ?,
               updated_at = CURRENT_TIMESTAMP
         WHERE user_id = ?
        """,
        (stored, user_id),
    )
    async with _cache_lock:
        if user_id in _cache:
            _cache[user_id][key] = value


async def invalidate(user_id: int | None = None) -> None:
    """Clear the in-memory cache for one user, or everyone if None."""
    async with _cache_lock:
        if user_id is None:
            _cache.clear()
        else:
            _cache.pop(user_id, None)


async def list_users_with_auto_scrape() -> list[dict[str, Any]]:
    """Return every user whose auto_scrape config has enabled=True.
    Used on bot startup to restore scheduled jobs."""
    rows = await db.fetchall(
        "SELECT user_id, auto_scrape_json FROM users "
        "WHERE auto_scrape_json IS NOT NULL",
    )
    out = []
    for row in rows:
        try:
            config = json.loads(row["auto_scrape_json"])
        except json.JSONDecodeError:
            continue
        if config and config.get("enabled"):
            out.append({"user_id": row["user_id"], "config": config})
    return out
