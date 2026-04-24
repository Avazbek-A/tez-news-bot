"""Persistent settings for the Spot News Bot.

Stores user preferences (voice, channel URL) in a JSON file
so they survive bot restarts. Uses atomic writes to prevent corruption.

In-memory cache avoids the repeated disk reads that previously happened
on every /status or /scrape (5+ reads per command).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from spot_bot.config import CHANNEL_URL, DEFAULT_LANGUAGE, DEFAULT_VOICE, TTS_RATE

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).parent / "user_settings.json"

_DEFAULTS = {
    "voice": DEFAULT_VOICE,
    "channel_url": CHANNEL_URL,
    "speed": TTS_RATE,
    "language": DEFAULT_LANGUAGE,
    "auto_scrape": None,
}


# In-memory cache — populated on first read, invalidated on every write.
# Settings are low-cardinality and written rarely, so a single-entry cache
# is sufficient. `None` means "not loaded yet".
_cache: dict[str, Any] | None = None


def _read_from_disk() -> dict[str, Any]:
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Settings load error (using defaults): %s", e)
    return dict(_DEFAULTS)


def load_settings() -> dict[str, Any]:
    """Load settings, using the in-memory cache if populated."""
    global _cache
    if _cache is None:
        _cache = _read_from_disk()
    # Return a copy so callers can't mutate the cache by mistake.
    return dict(_cache)


def save_settings(data: dict[str, Any]) -> None:
    """Atomically write settings to disk and update the cache.

    Writes to a temp file first, then renames to avoid corruption
    if the process is killed mid-write.
    """
    global _cache
    tmp_path = SETTINGS_PATH.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SETTINGS_PATH)
        _cache = dict(data)
    except OSError as e:
        logger.error("Settings save error: %s", e)
        # Clean up temp file if rename failed
        if tmp_path.exists():
            tmp_path.unlink()


def invalidate_cache() -> None:
    """Force the next load_settings() to re-read from disk.
    Useful after external modifications (tests, migrations)."""
    global _cache
    _cache = None


def get_setting(key: str) -> Any:
    """Get a single setting value."""
    return load_settings().get(key, _DEFAULTS.get(key))


def set_setting(key: str, value: Any) -> None:
    """Update a single setting and save to disk."""
    data = load_settings()
    data[key] = value
    save_settings(data)
