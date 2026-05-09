"""Help / about commands and the bot-identity setup.

This module owns:
- /help (index)
- /help_scrape, /help_auto, /help_audio, /help_filter, /help_library, /help_languages
- /about
- setMyCommands / setMyDescription / setMyShortDescription on startup

All strings flow through `t()` from translations.py so the help system
is always in the user's chosen UI language.
"""

from __future__ import annotations

import logging

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import Application, ContextTypes

from spot_bot.translations import t
from spot_bot.settings import get_setting

logger = logging.getLogger(__name__)


# Categories rendered in /help; each maps to a translation key prefix.
# /help_<key> renders the help_<key> translation entry.
_HELP_CATEGORIES = ("scrape", "auto", "audio", "filter", "library", "languages")


def _get_lang() -> str:
    return get_setting("language") or "en"


# ---------------------------------------------------------------------------
# /start — minimal welcome + quick-start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_full_help", lang),
                              callback_data="help_index")],
        [InlineKeyboardButton(t("btn_about", lang),
                              callback_data="help_about")],
    ])
    await update.message.reply_text(
        t("start_welcome", lang),
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# /help — index card
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """If invoked with no args: show the index. With one arg: show that
    category (alias for /help_<category>)."""
    lang = _get_lang()
    args = context.args or []
    if args:
        category = args[0].lower()
        if category in _HELP_CATEGORIES:
            await _render_category(update, context, category, lang)
            return
    await _render_help_index(update, context, lang)


async def _render_help_index(update_or_query, context, lang):
    text = t("help_index", lang)
    rows = []
    # Two-column grid of category buttons
    pairs = [_HELP_CATEGORIES[i:i + 2] for i in range(0, len(_HELP_CATEGORIES), 2)]
    for pair in pairs:
        row = []
        for cat in pair:
            row.append(InlineKeyboardButton(
                t(f"help_btn_{cat}", lang),
                callback_data=f"help_cat_{cat}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton(
        t("btn_about", lang),
        callback_data="help_about",
    )])
    keyboard = InlineKeyboardMarkup(rows)

    if hasattr(update_or_query, "message") and update_or_query.message is not None \
            and hasattr(update_or_query.message, "reply_text"):
        # It's an Update with a message
        await update_or_query.message.reply_text(text, reply_markup=keyboard)
    else:
        # It's a CallbackQuery
        try:
            await update_or_query.edit_message_text(text, reply_markup=keyboard)
        except Exception:
            await update_or_query.message.reply_text(text, reply_markup=keyboard)


async def _render_category(update_or_query, context, category, lang):
    body = t(f"help_{category}", lang)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t("btn_back_to_help", lang),
            callback_data="help_index",
        ),
    ]])
    if hasattr(update_or_query, "message") and update_or_query.message is not None \
            and hasattr(update_or_query.message, "reply_text"):
        await update_or_query.message.reply_text(body, reply_markup=keyboard)
    else:
        try:
            await update_or_query.edit_message_text(body, reply_markup=keyboard)
        except Exception:
            await update_or_query.message.reply_text(body, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# /help_<category> direct commands
# ---------------------------------------------------------------------------

def _make_help_category_handler(category: str):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        lang = _get_lang()
        await _render_category(update, context, category, lang)
    _handler.__name__ = f"cmd_help_{category}"
    return _handler


cmd_help_scrape = _make_help_category_handler("scrape")
cmd_help_auto = _make_help_category_handler("auto")
cmd_help_audio = _make_help_category_handler("audio")
cmd_help_filter = _make_help_category_handler("filter")
cmd_help_library = _make_help_category_handler("library")
cmd_help_languages = _make_help_category_handler("languages")


# ---------------------------------------------------------------------------
# /about
# ---------------------------------------------------------------------------

async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    text = t("about_body", lang)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t("btn_back_to_help", lang),
            callback_data="help_index",
        ),
    ]])
    await update.message.reply_text(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Inline button router for help / about
# ---------------------------------------------------------------------------

async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = _get_lang()
    data = query.data or ""

    try:
        await query.answer()
    except Exception:
        pass

    if data == "help_index":
        await _render_help_index(query, context, lang)
        return
    if data == "help_about":
        text = t("about_body", lang)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                t("btn_back_to_help", lang),
                callback_data="help_index",
            ),
        ]])
        try:
            await query.edit_message_text(text, reply_markup=kb)
        except Exception:
            await query.message.reply_text(text, reply_markup=kb)
        return
    if data.startswith("help_cat_"):
        category = data[len("help_cat_"):]
        if category in _HELP_CATEGORIES:
            await _render_category(query, context, category, lang)


# ---------------------------------------------------------------------------
# setMyCommands / setMyDescription / setMyShortDescription on startup
# ---------------------------------------------------------------------------

# The 14 commands shown in Telegram's `/` autocomplete menu. Order matters —
# users see them top-to-bottom.
_COMMAND_LIST_KEYS = [
    ("start",   "cmdmenu_start"),
    ("scrape",  "cmdmenu_scrape"),
    ("today",   "cmdmenu_today"),
    ("auto",    "cmdmenu_auto"),
    ("voice",   "cmdmenu_voice"),
    ("speed",   "cmdmenu_speed"),
    ("translate", "cmdmenu_translate"),
    ("summarize", "cmdmenu_summarize"),
    ("find",    "cmdmenu_find"),
    ("bookmarks", "cmdmenu_bookmarks"),
    ("stats",   "cmdmenu_stats"),
    ("status",  "cmdmenu_status"),
    ("help",    "cmdmenu_help"),
    ("about",   "cmdmenu_about"),
]


async def install_bot_identity(app: Application) -> None:
    """Set short description, long description, and per-language command
    menus via the Telegram Bot API. Called from bot._post_init."""
    bot = app.bot
    # Per-language command menu
    for code in ("en", "ru", "uz", "de", "tr"):
        try:
            commands = [
                BotCommand(cmd, t(key, code))
                for cmd, key in _COMMAND_LIST_KEYS
            ]
            await bot.set_my_commands(commands, language_code=code)
        except Exception as e:
            logger.warning("[identity] set_my_commands(%s) failed: %s", code, e)
    # Default command menu (no language) — fall back to English copy
    try:
        commands = [
            BotCommand(cmd, t(key, "en"))
            for cmd, key in _COMMAND_LIST_KEYS
        ]
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning("[identity] set_my_commands(default) failed: %s", e)

    # Descriptions: short (~120 chars) + long (~512 chars). Per-language.
    for code in ("en", "ru", "uz", "de", "tr"):
        try:
            await bot.set_my_short_description(
                t("bot_short_description", code),
                language_code=code,
            )
        except Exception as e:
            logger.warning("[identity] set_my_short_description(%s) failed: %s", code, e)
        try:
            await bot.set_my_description(
                t("bot_long_description", code),
                language_code=code,
            )
        except Exception as e:
            logger.warning("[identity] set_my_description(%s) failed: %s", code, e)
    logger.info("[identity] bot description + commands installed")
