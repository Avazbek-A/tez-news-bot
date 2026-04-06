import asyncio
import os
import re
import tempfile
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from spot_bot.config import (
    BOT_TOKEN,
    AVAILABLE_VOICES,
    VOICE_LANGUAGES,
    AVAILABLE_SPEEDS,
    AVAILABLE_LANGUAGES,
    DEFAULT_SCRAPE_COUNT,
    MAX_SCRAPE_COUNT,
    MAX_OFFSET,
    TTS_RATE,
    DEFAULT_AUTO_SCRAPE_COUNT,
    MIN_AUTO_INTERVAL_DAYS,
    MAX_AUTO_INTERVAL_DAYS,
)
from spot_bot.settings import get_setting, set_setting
from spot_bot.translations import t
from spot_bot.pipeline import run_pipeline
from spot_bot.delivery.telegram_sender import (
    send_articles_as_text,
    send_articles_as_file,
    send_article_images,
    send_audio_files,
    send_combined_audio,
)
from spot_bot.audio.tts_generator import (
    combine_audio_files,
    combine_audio_with_announcements,
    cleanup_audio_files,
)


_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")

# Active jobs per chat — allows /cancel to work
_running_jobs = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    await update.message.reply_text(t("start_help", lang))


# ---------------------------------------------------------------------------
# /scrape — launches pipeline as background task
# ---------------------------------------------------------------------------

async def cmd_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = _get_lang()

    # Reject if a job is already running for this chat
    if chat_id in _running_jobs:
        await update.message.reply_text(t("job_running", lang))
        return

    # Parse args
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

    for arg in args:
        range_match = _RANGE_PATTERN.match(arg)
        if range_match:
            val_a = int(range_match.group(1))
            val_b = int(range_match.group(2))
            # Normalize: either order works (31000-31050 or 31050-31000)
            hi = max(val_a, val_b)
            lo = min(val_a, val_b)
            if hi == lo:
                await update.message.reply_text(t("range_format", lang))
                return
            if hi - lo > MAX_SCRAPE_COUNT:
                await update.message.reply_text(
                    t("max_range", lang, max=MAX_SCRAPE_COUNT)
                )
                return
            # Auto-detect: both > MAX_OFFSET -> post IDs, otherwise offsets
            if hi > MAX_OFFSET and lo > MAX_OFFSET:
                start_post_id = hi   # newer (larger ID)
                end_post_id = lo     # older (smaller ID)
            else:
                start_offset = hi    # further from latest
                end_offset = lo      # closer to latest
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

    voice = _get_voice()
    rate = _get_speed()
    use_range = start_offset is not None and end_offset is not None
    use_post_ids = start_post_id is not None and end_post_id is not None

    # Build description for status message
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
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    status_msg = await update.message.reply_text(
        t("starting", lang, desc=f"{desc}{flag_str}")
    )

    # Create cancel event and launch as background task
    cancel_event = asyncio.Event()

    task = asyncio.create_task(
        _run_job(
            chat_id=chat_id,
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
            send_as_file=send_as_file,
            combined_audio=combined_audio,
            voice=voice,
            rate=rate,
            lang=lang,
        )
    )

    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def _run_job(*, chat_id, bot, status_msg, cancel_event,
                   use_range, use_post_ids=False, count=20,
                   start_offset=None, end_offset=None,
                   start_post_id=None, end_post_id=None,
                   include_audio=False, include_images=False,
                   send_as_file=True, combined_audio=False,
                   voice=None, rate=TTS_RATE, lang="en"):
    """Background task that runs the full pipeline + delivery."""
    result = None
    combined_path = None

    try:
        async def progress_callback(text):
            try:
                await status_msg.edit_text(text)
            except Exception:
                pass

        # Build pipeline kwargs
        pipeline_kwargs = dict(
            include_audio=include_audio,
            include_images=include_images,
            voice=voice,
            rate=rate,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
        if use_post_ids:
            pipeline_kwargs["start_post_id"] = start_post_id
            pipeline_kwargs["end_post_id"] = end_post_id
        elif use_range:
            pipeline_kwargs["start_offset"] = start_offset
            pipeline_kwargs["end_offset"] = end_offset
        else:
            pipeline_kwargs["count"] = count

        result = await run_pipeline(**pipeline_kwargs)

        if not result.articles:
            await status_msg.edit_text(t("no_articles", lang))
            return

        await status_msg.edit_text(
            t("sending_articles", lang, count=len(result.articles))
        )

        # Send text — as file or inline messages
        if send_as_file:
            await send_articles_as_file(bot, chat_id, result.articles)
        else:
            await send_articles_as_text(bot, chat_id, result.articles)

        # Send images if requested
        images_sent = 0
        if include_images:
            await status_msg.edit_text(t("sending_images", lang))
            images_sent = await send_article_images(
                bot, chat_id, result.articles
            )

        # Send audio if requested
        audio_sent = 0
        if include_audio and result.audio_results:
            if combined_audio:
                # Combine into one MP3 with title announcements
                await status_msg.edit_text(t("combining_audio", lang))
                tmpdir = tempfile.mkdtemp(prefix="spot_combined_")
                combined_path = os.path.join(tmpdir, "combined.mp3")
                combined_path = await combine_audio_with_announcements(
                    result.audio_results, combined_path, voice, rate,
                    announcement_prefix=t("announcement_prefix", lang),
                    untitled_text=t("untitled", lang),
                )
                if combined_path:
                    await status_msg.edit_text(t("sending_combined", lang))
                    success = await send_combined_audio(
                        bot, chat_id, combined_path,
                        len(result.articles),
                    )
                    if success:
                        audio_sent = sum(
                            1 for _, p in result.audio_results if p
                        )
                    else:
                        # File too large — fall back to individual files
                        await status_msg.edit_text(
                            t("combined_too_large", lang)
                        )
                        audio_sent = await send_audio_files(
                            bot, chat_id, result.audio_results
                        )
            else:
                await status_msg.edit_text(t("sending_audio", lang))
                audio_sent = await send_audio_files(
                    bot, chat_id, result.audio_results
                )

        # Final summary with post ID range
        parts = [t("articles_count", lang, n=len(result.articles))]
        if include_images:
            parts.append(t("images_count", lang, n=images_sent))
        if include_audio:
            parts.append(t("audio_count", lang, n=audio_sent))
        summary = t("done_sent", lang, parts=", ".join(parts))

        # Extract post ID range from articles for "next batch" hint
        post_ids = []
        for a in result.articles:
            if a.get("id"):
                pid = a["id"].split("/")[-1] if "/" in a.get("id", "") else None
                if pid and pid.isdigit():
                    post_ids.append(int(pid))
        if post_ids:
            newest_id = max(post_ids)
            oldest_id = min(post_ids)
            range_size = newest_id - oldest_id
            summary += "\n" + t("posts_range", lang,
                                oldest=oldest_id, newest=newest_id)
            if range_size > 0:
                summary += "\n" + t("next_batch", lang,
                                    start=newest_id,
                                    end=newest_id + range_size)

        await status_msg.edit_text(summary)

    except asyncio.CancelledError:
        try:
            await status_msg.edit_text(t("cancelled", lang))
        except Exception:
            pass

    except Exception as e:
        try:
            await status_msg.edit_text(t("error", lang, e=e))
        except Exception:
            pass

    finally:
        # Cleanup
        if result and result.audio_results:
            cleanup_audio_files(result.audio_results, combined_path)
        _running_jobs.pop(chat_id, None)


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = _get_lang()
    job = _running_jobs.get(chat_id)

    if not job:
        await update.message.reply_text(t("no_job", lang))
        return

    # Signal cancellation
    job["cancel_event"].set()
    job["task"].cancel()
    await update.message.reply_text(t("cancelling", lang))


# ---------------------------------------------------------------------------
# /voice
# ---------------------------------------------------------------------------

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()
    voice_list = _build_voice_list(lang)

    if not args:
        current = _get_voice()
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

    set_setting("voice", AVAILABLE_VOICES[name])
    await update.message.reply_text(
        t("voice_set", lang, voice=AVAILABLE_VOICES[name])
    )


# ---------------------------------------------------------------------------
# /speed
# ---------------------------------------------------------------------------

async def cmd_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()

    if not args:
        current = _get_speed()
        names = ", ".join(AVAILABLE_SPEEDS.keys())
        await update.message.reply_text(
            t("speed_current", lang, speed=current, presets=names)
        )
        return

    name = args[0].lower()

    # Check presets first
    if name in AVAILABLE_SPEEDS:
        rate = AVAILABLE_SPEEDS[name]
    elif re.match(r'^[+-]\d+%$', name):
        # Custom value like +30% or -20%
        rate = name
    else:
        names = ", ".join(AVAILABLE_SPEEDS.keys())
        await update.message.reply_text(
            t("speed_unknown", lang, name=name, presets=names)
        )
        return

    set_setting("speed", rate)
    await update.message.reply_text(t("speed_set", lang, speed=rate))


# ---------------------------------------------------------------------------
# /lang
# ---------------------------------------------------------------------------

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()

    if not args:
        await update.message.reply_text(t("lang_current", lang))
        return

    new_lang = args[0].lower()
    if new_lang not in AVAILABLE_LANGUAGES:
        await update.message.reply_text(
            t("lang_unknown", lang, code=new_lang)
        )
        return

    set_setting("language", new_lang)
    await update.message.reply_text(t("lang_set", new_lang))


# ---------------------------------------------------------------------------
# /channel
# ---------------------------------------------------------------------------

async def cmd_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()

    if not args:
        current = get_setting("channel_url")
        await update.message.reply_text(
            t("channel_current", lang, url=current)
        )
        return

    url = args[0].strip()
    if not url.startswith("https://t.me/s/"):
        await update.message.reply_text(t("channel_invalid", lang))
        return

    set_setting("channel_url", url)
    await update.message.reply_text(t("channel_set", lang, url=url))


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = _get_lang()
    voice = _get_voice()
    channel = get_setting("channel_url")
    speed = _get_speed()
    has_job = chat_id in _running_jobs

    # Auto-scrape status
    auto = get_setting("auto_scrape")
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

    # Language display
    lang_names = {"en": "English", "ru": "Русский", "uz": "O'zbek"}
    lang_display = lang_names.get(lang, lang)

    await update.message.reply_text(
        t("status", lang,
          channel=channel,
          voice=voice,
          speed=speed,
          language=lang_display,
          auto=auto_info,
          job=t("status_yes", lang) if has_job else t("status_no", lang),
          default_count=DEFAULT_SCRAPE_COUNT,
          max_count=MAX_SCRAPE_COUNT,
          max_offset=MAX_OFFSET)
    )


# ---------------------------------------------------------------------------
# /auto — scheduled auto-scrape
# ---------------------------------------------------------------------------

def _schedule_auto_scrape(app, config):
    """Schedule or reschedule the auto-scrape repeating job."""
    job_queue = app.job_queue
    if job_queue is None:
        print("WARNING: job-queue extra not installed. Auto-scrape unavailable.")
        return

    # Remove any existing auto-scrape job
    for job in job_queue.get_jobs_by_name("auto_scrape"):
        job.schedule_removal()

    if not config or not config.get("enabled"):
        return

    interval_seconds = config["interval_days"] * 86400
    job_queue.run_repeating(
        callback=_auto_scrape_callback,
        interval=interval_seconds,
        first=interval_seconds,
        name="auto_scrape",
        data=config,
    )


async def _auto_scrape_callback(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback — runs the scheduled scrape."""
    config = context.job.data
    chat_id = config["chat_id"]
    bot = context.bot
    lang = _get_lang()

    # Skip if a job is already running
    if chat_id in _running_jobs:
        try:
            await bot.send_message(chat_id, t("auto_skipped", lang))
        except Exception:
            pass
        return

    try:
        status_msg = await bot.send_message(chat_id, t("auto_starting", lang))
    except Exception:
        return

    cancel_event = asyncio.Event()
    voice = _get_voice()
    rate = _get_speed()

    task = asyncio.create_task(
        _run_job(
            chat_id=chat_id,
            bot=bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=False,
            count=config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
            start_offset=None,
            end_offset=None,
            include_audio=config.get("include_audio", False),
            include_images=config.get("include_images", False),
            send_as_file=config.get("send_as_file", True),
            combined_audio=config.get("combined_audio", False),
            voice=voice,
            rate=rate,
            lang=lang,
        )
    )
    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure auto-scrape scheduling."""
    args = context.args or []
    lang = _get_lang()

    # /auto — show status
    if not args:
        config = get_setting("auto_scrape")
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

    # /auto off
    if args[0].lower() == "off":
        config = get_setting("auto_scrape")
        if config:
            config["enabled"] = False
            set_setting("auto_scrape", config)
        _schedule_auto_scrape(context.application, None)
        await update.message.reply_text(t("auto_disabled", lang))
        return

    # /auto on [N] or /auto [count] [flags...]
    existing = get_setting("auto_scrape") or {}
    interval_days = existing.get("interval_days", 3)
    count = existing.get("count", DEFAULT_AUTO_SCRAPE_COUNT)
    include_audio = existing.get("include_audio", False)
    combined_audio = existing.get("combined_audio", False)
    include_images = existing.get("include_images", False)
    send_as_file = existing.get("send_as_file", True)

    remaining_args = list(args)
    if remaining_args[0].lower() == "on":
        remaining_args.pop(0)
        # Next number is interval in days
        if remaining_args and remaining_args[0].isdigit():
            interval_days = int(remaining_args.pop(0))

    # Parse remaining as scrape options (count, flags)
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

    # Validate interval
    if interval_days < MIN_AUTO_INTERVAL_DAYS or interval_days > MAX_AUTO_INTERVAL_DAYS:
        await update.message.reply_text(
            t("auto_interval_invalid", lang,
              min=MIN_AUTO_INTERVAL_DAYS, max=MAX_AUTO_INTERVAL_DAYS)
        )
        return

    config = {
        "enabled": True,
        "interval_days": interval_days,
        "chat_id": update.effective_chat.id,
        "count": count,
        "include_audio": include_audio,
        "combined_audio": combined_audio,
        "include_images": include_images,
        "send_as_file": send_as_file,
    }
    set_setting("auto_scrape", config)
    _schedule_auto_scrape(context.application, config)

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


async def _post_init(app: Application):
    """Restore scheduled jobs from persistent settings on startup."""
    config = get_setting("auto_scrape")
    if config and config.get("enabled"):
        _schedule_auto_scrape(app, config)
        print(f"Auto-scrape restored: every {config['interval_days']} day(s), "
              f"{config.get('count', DEFAULT_AUTO_SCRAPE_COUNT)} articles")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("scrape", cmd_scrape))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("speed", cmd_speed))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("channel", cmd_channel))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("auto", cmd_auto))

    return app
