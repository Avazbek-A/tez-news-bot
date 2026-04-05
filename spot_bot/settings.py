"""Persistent settings for the Spot News Bot.

Stores user preferences (voice, channel URL) in a JSON file
so they survive bot restarts. Uses atomic writes to prevent corruption.
"""
import json
import os
from pathlib import Path
from spot_bot.config import DEFAULT_VOICE, CHANNEL_URL

SETTINGS_PATH = Path(__file__).parent / "user_settings.json"

_DEFAULTS = {
    "voice": DEFAULT_VOICE,
    "channel_url": CHANNEL_URL,
    "auto_scrape": None,
}


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
