"""Persistent settings for the Spot News Bot.

Stores user preferences (voice, channel URL) in a JSON file
so they survive bot restarts. Uses atomic writes to prevent corruption.
"""
import json
import os
from pathlib import Path
from spot_bot.config import DEFAULT_VOICE, CHANNEL_URL, TTS_RATE, DEFAULT_LANGUAGE

import logging
logger = logging.getLogger(__name__)

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
    # Phase 5: multi-source. Items: {id, type ('telegram'|'rss'), url, label}.
    # If empty/None at load time, migrate from channel_url for backward compat.
    "sources": [],
    # When True, the cleaner keeps ad markers + contact footers so ad-style
    # articles arrive intact. Default False matches the historical behavior.
    "include_ads": False,
    # Phase 6: per-chat resume marker (set when user taps "📍 Mark here"
    # under a voice message). Shape: {"chat_id": int, "msg_id": int,
    # "marked_at": unix-epoch-int}. None when nothing marked yet.
    "resume_marker": None,
    # Phase 7: smart filtering
    # Min cleaned body length to keep an article. 0 disables.
    "quality_threshold": 200,
    # Title-similarity score (0-100). 100=disabled. Articles whose titles
    # match an earlier article in the batch above this threshold are
    # collapsed (only the first one is kept).
    "dup_threshold": 85,
    # Optional list of topic keywords. Empty list = topic filter disabled.
    # When non-empty, articles must contain at least one keyword (case-
    # insensitive substring against title + body head) to pass.
    "topics": [],
    # Phase 8: when True and GROQ_API_KEY is set, prepend a 2-3 sentence
    # LLM summary to each article's body. Cached in history_db so
    # re-scraping a known article skips the LLM call.
    "enable_summaries": False,
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
        logger.warning(f"Settings load error (using defaults): {e}")
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
        logger.warning(f"Settings save error: {e}")
        # Clean up temp file if rename failed
        if tmp_path.exists():
            tmp_path.unlink()


def get_setting(key):
    """Get a single setting value."""
    return load_settings().get(key, _DEFAULTS.get(key))


def get_sources():
    """Return the configured list of sources, auto-migrating from the
    legacy single channel_url if no `sources` list has been set yet.

    Each item is a dict {id, type, url, label}.
    """
    data = load_settings()
    sources = data.get("sources") or []
    if sources:
        return sources

    # Migrate from legacy channel_url
    legacy_url = data.get("channel_url")
    if legacy_url:
        migrated = [{
            "id": "default",
            "type": "telegram",
            "url": legacy_url,
            "label": "Default",
        }]
        data["sources"] = migrated
        save_settings(data)
        return migrated
    return []


def add_source(source):
    """Append a source dict {id, type, url, label}. Replaces if id already exists."""
    data = load_settings()
    sources = list(data.get("sources") or [])
    sources = [s for s in sources if s.get("id") != source["id"]]
    sources.append(source)
    data["sources"] = sources
    save_settings(data)


def remove_source(source_id):
    """Remove a source by id. Returns True if something was removed."""
    data = load_settings()
    sources = list(data.get("sources") or [])
    new_sources = [s for s in sources if s.get("id") != source_id]
    if len(new_sources) == len(sources):
        return False
    data["sources"] = new_sources
    save_settings(data)
    return True


def set_setting(key, value):
    """Update a single setting and save to disk."""
    data = load_settings()
    data[key] = value
    save_settings(data)
