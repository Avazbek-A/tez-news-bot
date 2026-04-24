"""Telegram bot: command handlers + app factory.

Background pipeline execution and auto-scrape scheduling live in
`spot_bot.jobs`. New feature commands (/latest, /filter, /save,
/favorites, /history) live in `spot_bot.handlers.features`. This file
keeps the classic settings/status commands plus `create_app()`.

All settings are per-user, scoped to `update.effective_user.id`.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from spot_bot.config import (
    AVAILABLE_LANGUAGES,
    AVAILABLE_SPEEDS,
    AVAILABLE_VOICES,
    BOT_TOKEN,
    DEFAULT_AUTO_SCRAPE_COUNT,
    DEFAULT_SCRAPE_COUNT,
    MAX_AUTO_INTERVAL_DAYS,
    MAX_OFFSET,
    MAX_SCRAPE_COUNT,
    MIN_AUTO_INTERVAL_DAYS,
    VOICE_LANGUAGES,
)
from spot_bot.handlers.features import (
    cmd_favorites,
    cmd_filter,
    cmd_history,
    cmd_latest,
    cmd_save,
    on_save_callback,
)
from spot_bot.jobs import run_job, running_jobs, schedule_auto_scrape
from spot_bot.storage import db as storage_db
from spot_bot.storage import user_settings
from spot_bot.translations import t

logger = logging.getLogger(__name__)

_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user(update: Update) -> tuple[int, int, str]:
    """Return (chat_id, user_id, lang) for the caller."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else chat_id
    lang = await user_settings.get(user_id, "lang") or "en"
    return chat_id, user_id, lang


def _build_voice_list(lang: str) -> str:
    """Build a formatted voice list grouped by language."""
    lines = []
    for lang_code, names in VOICE_LANGUAGES.items():
        label = t(f"lang_label_{lang_code}", lang)
        lines.append(f"{label}: {', '.join(names)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, _, lang = await _user(update)
    await update.message.reply_text(t("start_help", lang))


# ---------------------------------------------------------------------------
# /scrape
# ---------------------------------------------------------------------------


async def cmd_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id, user_id, lang = await _user(update)

    if user_id in running_jobs:
        await update.message.reply_text(t("job_running", lang))
        return

    args = context.args or []
    count = DEFAULT_SCRAPE_COUNT
    start_offset = None
    end_offset = None
    start_post_id = None
    end_post_id = None
    include_audio = False
    send_as_file = True
    include_images = False
    combined_audio = False
    include_summary = False

    for arg in args:
        range_match = _RANGE_PATTERN.match(arg)
        if range_match:
            val_a = int(range_match.group(1))
            val_b = int(range_match.group(2))
            hi = max(val_a, val_b)
            lo = min(val_a, val_b)
            if hi == lo:
                await update.message.reply_text(t("range_format", lang))
                return
            if hi - lo + 1 > MAX_SCRAPE_COUNT:
                await update.message.reply_text(
                    t("max_range", lang, max=MAX_SCRAPE_COUNT)
                )
                return
            if hi > MAX_OFFSET and lo > MAX_OFFSET:
                start_post_id = hi
                end_post_id = lo
            else:
                start_offset = hi
                end_offset = lo
                if start_offset > MAX_OFFSET:
                    await update.message.reply_text(
                        t("max_offset", lang, max=MAX_OFFSET)
                    )
                    return
        elif arg.isdigit():
            count = min(int(arg), MAX_SCRAPE_COUNT)
        elif arg.lower() == "audio":
            include_audio = True
        elif arg.lower() in ("file", "txt"):
            send_as_file = True
        elif arg.lower() == "inline":
            send_as_file = False
        elif arg.lower() in ("images", "img"):
            include_images = True
        elif arg.lower() == "combined":
            combined_audio = True
        elif arg.lower() in ("summary", "summarize", "ai"):
            include_summary = True

    voice = await user_settings.get(user_id, "voice")
    rate = await user_settings.get(user_id, "speed")
    use_range = start_offset is not None and end_offset is not None
    use_post_ids = start_post_id is not None and end_post_id is not None

    if use_post_ids:
        desc = f"posts #{end_post_id}-#{start_post_id}"
    elif use_range:
        desc = f"{start_offset}-{end_offset}"
    else:
        desc = f"latest {count}"
    flags = []
    if not send_as_file:
        flags.append("inline")
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    if include_images:
        flags.append("images")
    if include_summary:
        flags.append("summary")
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    status_msg = await update.message.reply_text(
        t("starting", lang, desc=f"{desc}{flag_str}")
    )

    cancel_event = asyncio.Event()

    task = asyncio.create_task(
        run_job(
            chat_id=chat_id,
            user_id=user_id,
            bot=context.bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=use_range,
            use_post_ids=use_post_ids,
            count=count,
            start_offset=start_offset,
            end_offset=end_offset,
            start_post_id=start_post_id,
            end_post_id=end_post_id,
            include_audio=include_audio,
            include_images=include_images,
            include_summary=include_summary,
            send_as_file=send_as_file,
            combined_audio=combined_audio,
            voice=voice,
            rate=rate,
            lang=lang,
        )
    )
    running_jobs[user_id] = {
        "task": task, "cancel_event": cancel_event, "chat_id": chat_id,
    }


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    job = running_jobs.get(user_id)
    if not job:
        await update.message.reply_text(t("no_job", lang))
        return
    job["cancel_event"].set()
    job["task"].cancel()
    await update.message.reply_text(t("cancelling", lang))


# ---------------------------------------------------------------------------
# /voice
# ---------------------------------------------------------------------------


async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []
    voice_list = _build_voice_list(lang)

    if not args:
        current = await user_settings.get(user_id, "voice")
        await update.message.reply_text(
            t("voice_current", lang, voice=current, voice_list=voice_list)
        )
        return

    name = args[0].lower()
    if name not in AVAILABLE_VOICES:
        await update.message.reply_text(
            t("voice_unknown", lang, name=name, voice_list=voice_list)
        )
        return

    await user_settings.set_value(user_id, "voice", AVAILABLE_VOICES[name])
    await update.message.reply_text(
        t("voice_set", lang, voice=AVAILABLE_VOICES[name])
    )


# ---------------------------------------------------------------------------
# /speed
# ---------------------------------------------------------------------------


async def cmd_speed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []

    if not args:
        current = await user_settings.get(user_id, "speed")
        names = ", ".join(AVAILABLE_SPEEDS.keys())
        await update.message.reply_text(
            t("speed_current", lang, speed=current, presets=names)
        )
        return

    name = args[0].lower()
    if name in AVAILABLE_SPEEDS:
        rate = AVAILABLE_SPEEDS[name]
    elif re.match(r"^[+-]\d+%$", name):
        rate = name
    else:
        names = ", ".join(AVAILABLE_SPEEDS.keys())
        await update.message.reply_text(
            t("speed_unknown", lang, name=name, presets=names)
        )
        return

    await user_settings.set_value(user_id, "speed", rate)
    await update.message.reply_text(t("speed_set", lang, speed=rate))


# ---------------------------------------------------------------------------
# /lang
# ---------------------------------------------------------------------------


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []

    if not args:
        await update.message.reply_text(t("lang_current", lang))
        return

    new_lang = args[0].lower()
    if new_lang not in AVAILABLE_LANGUAGES:
        await update.message.reply_text(
            t("lang_unknown", lang, code=new_lang)
        )
        return

    await user_settings.set_value(user_id, "lang", new_lang)
    await update.message.reply_text(t("lang_set", new_lang))


# ---------------------------------------------------------------------------
# /channel
# ---------------------------------------------------------------------------


async def cmd_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []

    if not args:
        current = await user_settings.get(user_id, "channel_url")
        await update.message.reply_text(
            t("channel_current", lang, url=current)
        )
        return

    url = args[0].strip()
    if not url.startswith("https://t.me/s/"):
        await update.message.reply_text(t("channel_invalid", lang))
        return

    await user_settings.set_value(user_id, "channel_url", url)
    await update.message.reply_text(t("channel_set", lang, url=url))


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    s = await user_settings.get_all(user_id)
    has_job = user_id in running_jobs

    auto = s.get("auto_scrape")
    if auto and auto.get("enabled"):
        auto_info = t("auto_status_on", lang,
                       days=auto["interval_days"],
                       count=auto.get("count", DEFAULT_AUTO_SCRAPE_COUNT))
        flags = []
        if auto.get("include_audio"):
            flags.append("combined audio" if auto.get("combined_audio") else "audio")
        if auto.get("include_images"):
            flags.append("images")
        if flags:
            auto_info += " + " + ", ".join(flags)
    else:
        auto_info = t("status_off", lang)

    lang_names = {"en": "English", "ru": "Русский", "uz": "O'zbek"}
    lang_display = lang_names.get(lang, lang)

    await update.message.reply_text(
        t("status", lang,
          channel=s["channel_url"],
          voice=s["voice"],
          speed=s["speed"],
          language=lang_display,
          auto=auto_info,
          job=t("status_yes", lang) if has_job else t("status_no", lang),
          default_count=DEFAULT_SCRAPE_COUNT,
          max_count=MAX_SCRAPE_COUNT,
          max_offset=MAX_OFFSET)
    )


# ---------------------------------------------------------------------------
# /auto
# ---------------------------------------------------------------------------


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id, user_id, lang = await _user(update)
    args = context.args or []

    if not args:
        config = await user_settings.get(user_id, "auto_scrape")
        if config and config.get("enabled"):
            flags = []
            if config.get("include_audio"):
                flags.append("combined audio" if config.get("combined_audio") else "audio")
            if config.get("include_images"):
                flags.append("images")
            flag_str = (" + " + ", ".join(flags)) if flags else ""
            await update.message.reply_text(
                t("auto_show_on", lang,
                  days=config["interval_days"],
                  count=config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
                  flags=flag_str)
            )
        else:
            await update.message.reply_text(t("auto_show_off", lang))
        return

    if args[0].lower() == "off":
        config = await user_settings.get(user_id, "auto_scrape")
        if config:
            config["enabled"] = False
            await user_settings.set_value(user_id, "auto_scrape", config)
        schedule_auto_scrape(context.application, None)
        await update.message.reply_text(t("auto_disabled", lang))
        return

    existing = (await user_settings.get(user_id, "auto_scrape")) or {}
    interval_days = existing.get("interval_days", 3)
    count = existing.get("count", DEFAULT_AUTO_SCRAPE_COUNT)
    include_audio = existing.get("include_audio", False)
    combined_audio = existing.get("combined_audio", False)
    include_images = existing.get("include_images", False)
    send_as_file = existing.get("send_as_file", True)

    remaining_args = list(args)
    if remaining_args[0].lower() == "on":
        remaining_args.pop(0)
        if remaining_args and remaining_args[0].isdigit():
            interval_days = int(remaining_args.pop(0))

    for arg in remaining_args:
        if arg.isdigit():
            count = min(int(arg), MAX_SCRAPE_COUNT)
        elif arg.lower() == "audio":
            include_audio = True
        elif arg.lower() == "combined":
            combined_audio = True
        elif arg.lower() in ("images", "img"):
            include_images = True
        elif arg.lower() == "inline":
            send_as_file = False
        elif arg.lower() in ("file", "txt"):
            send_as_file = True

    if interval_days < MIN_AUTO_INTERVAL_DAYS or interval_days > MAX_AUTO_INTERVAL_DAYS:
        await update.message.reply_text(
            t("auto_interval_invalid", lang,
              min=MIN_AUTO_INTERVAL_DAYS, max=MAX_AUTO_INTERVAL_DAYS)
        )
        return

    config = {
        "enabled": True,
        "interval_days": interval_days,
        "chat_id": chat_id,
        "user_id": user_id,
        "count": count,
        "include_audio": include_audio,
        "combined_audio": combined_audio,
        "include_images": include_images,
        "send_as_file": send_as_file,
    }
    await user_settings.set_value(user_id, "auto_scrape", config)
    schedule_auto_scrape(context.application, config)

    flags = []
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    if include_images:
        flags.append("images")
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    await update.message.reply_text(
        t("auto_enabled", lang,
          days=interval_days, count=count, flags=flag_str)
    )


# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------


async def _post_init(app: Application) -> None:
    """Open DB + restore scheduled auto-scrapes for every user."""
    await storage_db.connect()
    await user_settings.migrate_legacy_json_if_needed()

    rows = await user_settings.list_users_with_auto_scrape()
    for row in rows:
        config = row["config"]
        # Older configs may lack user_id — fall back to chat_id.
        config.setdefault("user_id", row["user_id"])
        schedule_auto_scrape(app, config)
        logger.info(
            "Auto-scrape restored for user %s: every %d day(s), %d articles",
            row["user_id"], config["interval_days"],
            config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
        )


async def _post_shutdown(app: Application) -> None:
    """Release browser + DB on shutdown."""
    from spot_bot.scrapers.browser_pool import shutdown as browser_shutdown
    await browser_shutdown()
    await storage_db.close()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> Any:
    """Create and configure the Telegram bot application."""
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    # Classic commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("scrape", cmd_scrape))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("speed", cmd_speed))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("channel", cmd_channel))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("auto", cmd_auto))

    # Phase 5 feature commands
    app.add_handler(CommandHandler("latest", cmd_latest))
    app.add_handler(CommandHandler("filter", cmd_filter))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("favorites", cmd_favorites))
    app.add_handler(CommandHandler("history", cmd_history))

    # Inline ⭐ Save button
    app.add_handler(CallbackQueryHandler(on_save_callback, pattern=r"^fav:"))

    return app
