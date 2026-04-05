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
    DEFAULT_SCRAPE_COUNT,
    MAX_SCRAPE_COUNT,
    MAX_OFFSET,
    TTS_RATE,
    DEFAULT_AUTO_SCRAPE_COUNT,
    MIN_AUTO_INTERVAL_DAYS,
    MAX_AUTO_INTERVAL_DAYS,
)
from spot_bot.settings import get_setting, set_setting
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


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Spot News Bot\n\n"
        "Scraping:\n"
        "/scrape 50 — Latest 50 as .txt file\n"
        "/scrape 50 inline — Latest 50 as individual messages\n"
        "/scrape 50 audio — .txt + individual MP3s\n"
        "/scrape 50 audio combined — .txt + one combined MP3\n"
        "/scrape 2000-1950 — Posts #2000 to #1950 from latest\n"
        "/scrape 50 images — .txt + article images\n\n"
        "Auto-scrape:\n"
        "/auto — Show auto-scrape status\n"
        "/auto on 3 — Enable every 3 days\n"
        "/auto 50 audio combined — Set what to auto-scrape\n"
        "/auto off — Disable auto-scrape\n\n"
        "Control:\n"
        "/cancel — Stop a running job\n\n"
        "Settings:\n"
        "/voice dmitry — Switch to male voice\n"
        "/voice svetlana — Switch to female voice\n"
        "/channel — Show/change source channel\n"
        "/status — Show current settings"
    )


# ---------------------------------------------------------------------------
# /scrape — launches pipeline as background task
# ---------------------------------------------------------------------------

async def cmd_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Reject if a job is already running for this chat
    if chat_id in _running_jobs:
        await update.message.reply_text(
            "A job is already running. Use /cancel to stop it first."
        )
        return

    # Parse args
    args = context.args or []
    count = DEFAULT_SCRAPE_COUNT
    start_offset = None
    end_offset = None
    include_audio = False
    send_as_file = True  # NEW DEFAULT: file delivery
    include_images = False
    combined_audio = False

    for arg in args:
        range_match = _RANGE_PATTERN.match(arg)
        if range_match:
            start_offset = int(range_match.group(1))
            end_offset = int(range_match.group(2))
            if start_offset <= end_offset:
                await update.message.reply_text(
                    "Range format: START-END where START > END.\n"
                    "Example: /scrape 2000-1950 (gets 50 posts)"
                )
                return
            if start_offset > MAX_OFFSET:
                await update.message.reply_text(
                    f"Max offset is {MAX_OFFSET}."
                )
                return
            if start_offset - end_offset > MAX_SCRAPE_COUNT:
                await update.message.reply_text(
                    f"Max range size is {MAX_SCRAPE_COUNT} posts."
                )
                return
        elif arg.isdigit():
            count = min(int(arg), MAX_SCRAPE_COUNT)
        elif arg.lower() == "audio":
            include_audio = True
        elif arg.lower() in ("file", "txt"):
            send_as_file = True  # Redundant but backward-compatible
        elif arg.lower() == "inline":
            send_as_file = False
        elif arg.lower() in ("images", "img"):
            include_images = True
        elif arg.lower() == "combined":
            combined_audio = True

    voice = _get_voice()
    use_range = start_offset is not None and end_offset is not None

    # Build description for status message
    desc = f"{start_offset}-{end_offset}" if use_range else f"latest {count}"
    flags = []
    if not send_as_file:
        flags.append("inline")
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    if include_images:
        flags.append("images")
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    status_msg = await update.message.reply_text(
        f"Starting: {desc}{flag_str}..."
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
            count=count,
            start_offset=start_offset,
            end_offset=end_offset,
            include_audio=include_audio,
            include_images=include_images,
            send_as_file=send_as_file,
            combined_audio=combined_audio,
            voice=voice,
        )
    )

    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def _run_job(*, chat_id, bot, status_msg, cancel_event,
                   use_range, count, start_offset, end_offset,
                   include_audio, include_images, send_as_file,
                   combined_audio, voice):
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
            rate=TTS_RATE,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
        if use_range:
            pipeline_kwargs["start_offset"] = start_offset
            pipeline_kwargs["end_offset"] = end_offset
        else:
            pipeline_kwargs["count"] = count

        result = await run_pipeline(**pipeline_kwargs)

        if not result.articles:
            await status_msg.edit_text("No articles found.")
            return

        await status_msg.edit_text(
            f"Sending {len(result.articles)} articles..."
        )

        # Send text — as file or inline messages
        if send_as_file:
            await send_articles_as_file(bot, chat_id, result.articles)
        else:
            await send_articles_as_text(bot, chat_id, result.articles)

        # Send images if requested
        images_sent = 0
        if include_images:
            await status_msg.edit_text("Sending images...")
            images_sent = await send_article_images(
                bot, chat_id, result.articles
            )

        # Send audio if requested
        audio_sent = 0
        if include_audio and result.audio_results:
            if combined_audio:
                # Combine into one MP3 with title announcements
                await status_msg.edit_text("Combining audio with announcements...")
                tmpdir = tempfile.mkdtemp(prefix="spot_combined_")
                combined_path = os.path.join(tmpdir, "combined.mp3")
                combined_path = await combine_audio_with_announcements(
                    result.audio_results, combined_path, voice, TTS_RATE
                )
                if combined_path:
                    await status_msg.edit_text("Sending combined audio...")
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
                            "Combined file too large, sending individually..."
                        )
                        audio_sent = await send_audio_files(
                            bot, chat_id, result.audio_results
                        )
            else:
                await status_msg.edit_text("Sending audio files...")
                audio_sent = await send_audio_files(
                    bot, chat_id, result.audio_results
                )

        # Final summary
        parts = [f"{len(result.articles)} articles"]
        if include_images:
            parts.append(f"{images_sent} images")
        if include_audio:
            parts.append(f"{audio_sent} audio")
        summary = "Done! Sent " + ", ".join(parts) + "."
        await status_msg.edit_text(summary)

    except asyncio.CancelledError:
        try:
            await status_msg.edit_text("Job cancelled.")
        except Exception:
            pass

    except Exception as e:
        try:
            await status_msg.edit_text(f"Error: {e}")
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
    job = _running_jobs.get(chat_id)

    if not job:
        await update.message.reply_text("No active job to cancel.")
        return

    # Signal cancellation
    job["cancel_event"].set()
    job["task"].cancel()
    await update.message.reply_text("Cancelling...")


# ---------------------------------------------------------------------------
# /voice
# ---------------------------------------------------------------------------

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []

    if not args:
        current = _get_voice()
        names = ", ".join(AVAILABLE_VOICES.keys())
        await update.message.reply_text(
            f"Current voice: {current}\nAvailable: {names}\n"
            f"Usage: /voice dmitry"
        )
        return

    name = args[0].lower()
    if name not in AVAILABLE_VOICES:
        names = ", ".join(AVAILABLE_VOICES.keys())
        await update.message.reply_text(
            f"Unknown voice '{name}'. Available: {names}"
        )
        return

    set_setting("voice", AVAILABLE_VOICES[name])
    await update.message.reply_text(f"Voice set to: {AVAILABLE_VOICES[name]}")


# ---------------------------------------------------------------------------
# /channel
# ---------------------------------------------------------------------------

async def cmd_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []

    if not args:
        current = get_setting("channel_url")
        await update.message.reply_text(
            f"Current channel: {current}\n\n"
            f"To change: /channel https://t.me/s/channel_name"
        )
        return

    url = args[0].strip()
    if not url.startswith("https://t.me/s/"):
        await update.message.reply_text(
            "URL must start with https://t.me/s/\n"
            "Example: /channel https://t.me/s/spotuz"
        )
        return

    set_setting("channel_url", url)
    await update.message.reply_text(f"Channel set to: {url}")


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    voice = _get_voice()
    channel = get_setting("channel_url")
    has_job = chat_id in _running_jobs

    # Auto-scrape status
    auto = get_setting("auto_scrape")
    if auto and auto.get("enabled"):
        auto_info = f"Every {auto['interval_days']}d, {auto.get('count', DEFAULT_AUTO_SCRAPE_COUNT)} articles"
        flags = []
        if auto.get("include_audio"):
            flags.append("combined audio" if auto.get("combined_audio") else "audio")
        if auto.get("include_images"):
            flags.append("images")
        if flags:
            auto_info += " + " + ", ".join(flags)
    else:
        auto_info = "Off"

    await update.message.reply_text(
        f"Channel: {channel}\n"
        f"Voice: {voice}\n"
        f"Auto-scrape: {auto_info}\n"
        f"Active job: {'Yes' if has_job else 'No'}\n"
        f"Default count: {DEFAULT_SCRAPE_COUNT}\n"
        f"Max count: {MAX_SCRAPE_COUNT}\n"
        f"Max offset: {MAX_OFFSET}"
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

    # Skip if a job is already running
    if chat_id in _running_jobs:
        try:
            await bot.send_message(chat_id, "Auto-scrape skipped: a job is already running.")
        except Exception:
            pass
        return

    try:
        status_msg = await bot.send_message(chat_id, "Auto-scrape starting...")
    except Exception:
        return

    cancel_event = asyncio.Event()
    voice = _get_voice()

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
        )
    )
    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure auto-scrape scheduling."""
    args = context.args or []

    # /auto — show status
    if not args:
        config = get_setting("auto_scrape")
        if config and config.get("enabled"):
            info = f"Every {config['interval_days']} day(s), {config.get('count', DEFAULT_AUTO_SCRAPE_COUNT)} articles"
            flags = []
            if config.get("include_audio"):
                flags.append("combined audio" if config.get("combined_audio") else "audio")
            if config.get("include_images"):
                flags.append("images")
            if flags:
                info += " + " + ", ".join(flags)
            await update.message.reply_text(f"Auto-scrape: {info}")
        else:
            await update.message.reply_text(
                "Auto-scrape: Off\n\n"
                "Usage:\n"
                "/auto on 3 — Enable every 3 days\n"
                "/auto 50 audio combined — Set options\n"
                "/auto off — Disable"
            )
        return

    # /auto off
    if args[0].lower() == "off":
        config = get_setting("auto_scrape")
        if config:
            config["enabled"] = False
            set_setting("auto_scrape", config)
        _schedule_auto_scrape(context.application, None)
        await update.message.reply_text("Auto-scrape disabled.")
        return

    # /auto on [N] or /auto [count] [flags...]
    # Parse interval and scrape options
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
            f"Interval must be {MIN_AUTO_INTERVAL_DAYS}-{MAX_AUTO_INTERVAL_DAYS} days."
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
        f"Auto-scrape enabled: every {interval_days} day(s), "
        f"{count} articles{flag_str}."
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
    app.add_handler(CommandHandler("channel", cmd_channel))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("auto", cmd_auto))

    return app
