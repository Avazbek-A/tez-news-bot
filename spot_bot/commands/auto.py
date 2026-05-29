"""Scheduled auto-scrape: /auto + the JobQueue scheduling/callback.

Depends on common + runner. `_schedule_auto_scrape` is also called by
bot.py's _post_init on startup to restore a saved schedule.
"""
import asyncio
import logging
from datetime import timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.config import (
    DEFAULT_AUTO_SCRAPE_COUNT,
    MAX_SCRAPE_COUNT,
    MIN_AUTO_INTERVAL_DAYS,
    MAX_AUTO_INTERVAL_DAYS,
)
from spot_bot.settings import get_setting, set_setting
from spot_bot.translations import t
from spot_bot.commands.common import (
    _running_jobs,
    _DEFAULT_TZ_OFFSET_HOURS,
    _get_lang,
    _get_voice,
    _get_speed,
)
from spot_bot.commands.runner import _run_job

logger = logging.getLogger(__name__)


_WEEKDAY_NAMES = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}


def _parse_hh_mm(text: str):
    """Parse 'HH:MM' string to (hour, minute) ints, or raise ValueError."""
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected HH:MM, got {text!r}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"HH:MM out of range: {text!r}")
    return h, m


def _schedule_auto_scrape(app, config):
    """Schedule or reschedule the auto-scrape job.

    Supports two modes (selected via config['mode']):
    - 'interval': run every N days (config['interval_days'])
    - 'cron': run at a specific HH:MM on chosen weekdays
              (config['schedule'] = {hour, minute, days})
    """
    job_queue = app.job_queue
    if job_queue is None:
        logger.warning("job-queue extra not installed. Auto-scrape unavailable.")
        return

    # Remove any existing auto-scrape job
    for job in job_queue.get_jobs_by_name("auto_scrape"):
        job.schedule_removal()

    if not config or not config.get("enabled"):
        return

    mode = config.get("mode", "interval")

    if mode == "cron":
        sched = config.get("schedule") or {}
        hh = int(sched.get("hour", 8))
        mm = int(sched.get("minute", 0))
        days = tuple(sched.get("days") or range(7))
        tz_offset = int(config.get("tz_offset_hours", _DEFAULT_TZ_OFFSET_HOURS))

        from datetime import time as time_cls
        tz = timezone(timedelta(hours=tz_offset))
        run_time = time_cls(hour=hh, minute=mm, tzinfo=tz)
        job_queue.run_daily(
            callback=_auto_scrape_callback,
            time=run_time,
            days=days,
            name="auto_scrape",
            data=config,
        )
        logger.info(
            "Auto-scrape scheduled cron: %02d:%02d UTC%+d on days=%s",
            hh, mm, tz_offset, days,
        )
        return

    # interval mode (back-compat)
    interval_seconds = int(config.get("interval_days", 3)) * 86400
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
    chronological = (get_setting("chronological_order") == "oldest_first")

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
            chronological=chronological,
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

    # /auto <subcommand> ... where subcommand is:
    #   daily HH:MM ...
    #   weekdays HH:MM ...
    #   weekly Mon HH:MM ...
    #   every N ...      (N-day interval)
    #   on [N] ...       (back-compat = `every N`)
    existing = get_setting("auto_scrape") or {}
    count = existing.get("count", DEFAULT_AUTO_SCRAPE_COUNT)
    include_audio = existing.get("include_audio", False)
    combined_audio = existing.get("combined_audio", False)
    include_images = existing.get("include_images", False)
    send_as_file = existing.get("send_as_file", True)
    tz_offset = existing.get("tz_offset_hours", _DEFAULT_TZ_OFFSET_HOURS)

    remaining_args = list(args)
    sub = remaining_args.pop(0).lower()

    mode = None
    interval_days = None
    schedule = None

    try:
        if sub == "daily":
            hh, mm = _parse_hh_mm(remaining_args.pop(0))
            mode = "cron"
            schedule = {"hour": hh, "minute": mm, "days": list(range(7))}
        elif sub == "weekdays":
            hh, mm = _parse_hh_mm(remaining_args.pop(0))
            mode = "cron"
            schedule = {"hour": hh, "minute": mm, "days": [0, 1, 2, 3, 4]}
        elif sub == "weekly":
            day_name = remaining_args.pop(0).lower()
            if day_name not in _WEEKDAY_NAMES:
                raise ValueError(f"unknown weekday: {day_name}")
            hh, mm = _parse_hh_mm(remaining_args.pop(0))
            mode = "cron"
            schedule = {
                "hour": hh, "minute": mm,
                "days": [_WEEKDAY_NAMES[day_name]],
            }
        elif sub == "every":
            interval_days = int(remaining_args.pop(0))
            mode = "interval"
        elif sub == "on":
            # back-compat: /auto on [N] = /auto every N
            mode = "interval"
            if remaining_args and remaining_args[0].isdigit():
                interval_days = int(remaining_args.pop(0))
            else:
                interval_days = existing.get("interval_days", 3)
        else:
            await update.message.reply_text(t("auto_usage", lang))
            return
    except (IndexError, ValueError) as e:
        await update.message.reply_text(t("auto_bad_syntax", lang, err=str(e)))
        return

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

    # Validate interval mode bounds
    if mode == "interval":
        if interval_days < MIN_AUTO_INTERVAL_DAYS or interval_days > MAX_AUTO_INTERVAL_DAYS:
            await update.message.reply_text(
                t("auto_interval_invalid", lang,
                  min=MIN_AUTO_INTERVAL_DAYS, max=MAX_AUTO_INTERVAL_DAYS)
            )
            return

    config = {
        "enabled": True,
        "mode": mode,
        "chat_id": update.effective_chat.id,
        "count": count,
        "include_audio": include_audio,
        "combined_audio": combined_audio,
        "include_images": include_images,
        "send_as_file": send_as_file,
        "tz_offset_hours": tz_offset,
    }
    if mode == "interval":
        config["interval_days"] = interval_days
    else:
        config["schedule"] = schedule

    set_setting("auto_scrape", config)
    _schedule_auto_scrape(context.application, config)

    flags = []
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    if include_images:
        flags.append("images")
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    if mode == "cron":
        s = config["schedule"]
        days_label = _format_days_label(s["days"], lang)
        await update.message.reply_text(
            t("auto_enabled_cron", lang,
              days=days_label,
              hour=s["hour"], minute=s["minute"],
              count=count, flags=flag_str)
        )
    else:
        await update.message.reply_text(
            t("auto_enabled", lang,
              days=interval_days, count=count, flags=flag_str)
        )


def _format_days_label(days, lang):
    """Human-readable label for a list of weekday integers (0=Mon)."""
    if sorted(days) == list(range(7)):
        return t("days_every_day", lang)
    if sorted(days) == [0, 1, 2, 3, 4]:
        return t("days_weekdays", lang)
    if len(days) == 1:
        return t(f"day_{days[0]}", lang)
    return ", ".join(t(f"day_{d}", lang) for d in sorted(days))
