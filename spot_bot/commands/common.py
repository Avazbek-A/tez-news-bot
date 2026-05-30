"""Shared state, helpers, and constants for the command modules.

This is the bottom of the commands dependency graph — every other
command module may import from here, but this module imports from none of
them (so there are no cycles). It holds the mutable per-chat state that
several handlers coordinate through (active jobs, pending confirmations,
pending scrape-menu configs) plus the small settings accessors.
"""
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from spot_bot.config import VOICE_LANGUAGES
from spot_bot.settings import get_setting
from spot_bot.translations import t


_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")

# Active jobs per chat — allows /cancel to work. Mutated in place by the
# scrape launcher, the runner's finally block, /cancel, and /status, so
# they must all reference this one dict object.
_running_jobs: dict = {}

# Pending confirmation requests for title-anchored scrapes (keyed by
# chat_id). See _ask_anchor_confirmation in runner.py.
_pending_confirmations: dict = {}

# How long to wait for the user to click Confirm/Cancel (seconds).
CONFIRM_TIMEOUT = 300

# Pending /scrape menu state per chat (keyed by chat_id).
_pending_scrape_configs: dict = {}

# Languages the bot can translate to (used by /scrape translate=<lang> and
# /translate).
_TRANSLATE_LANGS = {"en", "ru", "uz", "de", "tr"}

# Default user timezone (Tashkent, UTC+5) for date-shortcut + auto-scrape
# scheduling. Shared by the date commands and /auto.
_DEFAULT_TZ_OFFSET_HOURS = 5


def _get_voice():
    return get_setting("voice")


def _get_speed():
    return get_setting("speed")


def _get_lang():
    return get_setting("language") or "en"


def _build_voice_list(lang):
    """Build a formatted voice list grouped by language."""
    lines = []
    for lang_code, names in VOICE_LANGUAGES.items():
        label = t(f"lang_label_{lang_code}", lang)
        lines.append(f"{label}: {', '.join(names)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# One-tap "next batch" button
#
# The delivery card used to suggest "/scrape <start>-<end>" as text, but
# Telegram only makes the bare "/scrape" tappable — the IDs had to be
# copied by hand. Instead we attach an inline button whose callback_data
# encodes the next older ID window plus a compact flags string, so one tap
# repeats the scrape (same format) over the next batch.
# ---------------------------------------------------------------------------

NEXT_BATCH_PREFIX = "nb_"


def encode_next_batch_flags(*, include_audio, combined_audio, include_images,
                            send_as_file, include_seen) -> str:
    """Pack the delivery options into a short string for callback_data."""
    f = ""
    if combined_audio:
        f += "c"
    elif include_audio:
        f += "a"
    if include_images:
        f += "m"
    if not send_as_file:
        f += "i"
    if include_seen:
        f += "s"
    return f or "t"  # 't' = plain text/file default


def decode_next_batch_flags(flags: str) -> dict:
    """Inverse of encode_next_batch_flags."""
    combined = "c" in flags
    return {
        "include_audio": combined or "a" in flags,
        "combined_audio": combined,
        "include_images": "m" in flags,
        "send_as_file": "i" not in flags,
        "include_seen": "s" in flags,
    }


def next_batch_keyboard(start_id, end_id, n, flags, lang):
    """Inline keyboard with a single 'Next N' button for the next batch."""
    cb = f"{NEXT_BATCH_PREFIX}{start_id}_{end_id}_{flags}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("next_batch_btn", lang, n=n), callback_data=cb),
    ]])
