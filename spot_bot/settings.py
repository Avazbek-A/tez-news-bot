"""Persistent settings for the Spot News Bot.

Stores user preferences (voice, channel URL) in a JSON file
so they survive bot restarts. Uses atomic writes to prevent corruption.
"""
import json
import os
from pathlib import Path
from spot_bot.config import DEFAULT_VOICE, CHANNEL_URL, TTS_RATE, DEFAULT_LANGUAGE

SETTINGS_PATH = Path(__file__).parent / "user_settings.json"

_DEFAULTS = {
    "voice": DEFAULT_VOICE,
    "channel_url": CHANNEL_URL,
    "speed": TTS_RATE,
    "language": DEFAULT_LANGUAGE,
    "auto_scrape": None,
    "chronological_order": "newest_first",
    # Phase 4: reading log + bookmarks
    "delivered_post_ids": [],   # capped at DELIVERED_LOG_MAX (most-recent kept)
    "bookmarked_post_ids": [],
}

# Cap on the in-memory reading log so user_settings.json doesn't grow forever.
DELIVERED_LOG_MAX = 5000


def remember_delivered(post_ids):
    """Append numeric post IDs to the delivered log, dedupe, and trim
    to DELIVERED_LOG_MAX (keeping the highest IDs)."""
    if not post_ids:
        return
    data = load_settings()
    existing = set(data.get("delivered_post_ids") or [])
    existing.update(int(pid) for pid in post_ids if pid is not None)
    if len(existing) > DELIVERED_LOG_MAX:
        # Keep the most-recent (highest) IDs only.
        existing = set(sorted(existing)[-DELIVERED_LOG_MAX:])
    data["delivered_post_ids"] = sorted(existing)
    save_settings(data)


def add_bookmark(post_id):
    """Add a numeric post ID to bookmarks (no-op if already there)."""
    data = load_settings()
    bookmarks = list(data.get("bookmarked_post_ids") or [])
    if int(post_id) not in bookmarks:
        bookmarks.append(int(post_id))
        bookmarks.sort()
        data["bookmarked_post_ids"] = bookmarks
        save_settings(data)


def remove_bookmark(post_id):
    """Remove a numeric post ID from bookmarks if present. Returns True if
    something was removed."""
    data = load_settings()
    bookmarks = list(data.get("bookmarked_post_ids") or [])
    target = int(post_id)
    if target in bookmarks:
        bookmarks.remove(target)
        data["bookmarked_post_ids"] = bookmarks
        save_settings(data)
        return True
    return False


def load_settings():
    """Load settings from disk. Returns defaults if file missing or corrupt."""
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults (in case new keys were added)
            merged = {**_DEFAULTS, **data}
            return merged
    except (json.JSONDecodeError, OSError) as e:
        print(f"Settings load error (using defaults): {e}")
    return dict(_DEFAULTS)


def save_settings(data):
    """Atomically write settings to disk.

    Writes to a temp file first, then renames to avoid corruption
    if the process is killed mid-write.
    """
    tmp_path = SETTINGS_PATH.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SETTINGS_PATH)
    except OSError as e:
        print(f"Settings save error: {e}")
        # Clean up temp file if rename failed
        if tmp_path.exists():
            tmp_path.unlink()


def get_setting(key):
    """Get a single setting value."""
    return load_settings().get(key, _DEFAULTS.get(key))


def set_setting(key, value):
    """Update a single setting and save to disk."""
    data = load_settings()
    data[key] = value
    save_settings(data)
