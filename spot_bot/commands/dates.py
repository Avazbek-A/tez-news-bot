"""Date-based scrape shortcuts: /today, /yesterday, /thisweek, /since.

Each resolves a date window to a post-ID range via the scraper, then
launches the shared runner. Depends on common + runner.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from spot_bot.settings import get_setting
from spot_bot.translations import t
from spot_bot.scrapers.telegram_channel import find_post_ids_for_date_range
from spot_bot.commands.common import (
    _running_jobs,
    _DEFAULT_TZ_OFFSET_HOURS,
    _get_lang,
    _get_voice,
    _get_speed,
)
from spot_bot.commands.runner import _run_job

logger = logging.getLogger(__name__)


def _local_today():
    """Return today's date in the bot's default local timezone."""
    tz = timezone(timedelta(hours=_DEFAULT_TZ_OFFSET_HOURS))
    return datetime.now(tz).date()


async def _scrape_date_range(update, context, start_date, end_date,
                             extra_args, label_for_status):
    """Resolve [start_date, end_date] to a post-ID range and dispatch a scrape.

    extra_args are the trailing flags from the user's command (e.g.
    ['audio', 'combined']). They're parsed identically to /scrape's flags.
    """
    chat_id = update.effective_chat.id
    lang = _get_lang()

    if chat_id in _running_jobs:
        await update.message.reply_text(t("job_running", lang))
        return

    status_msg = await update.message.reply_text(
        t("date_resolving", lang, label=label_for_status)
    )

    try:
        channel_url = get_setting("channel_url")
        newest_id, oldest_id = await find_post_ids_for_date_range(
            start_date, end_date, channel_url=channel_url,
            progress_callback=lambda m: status_msg.edit_text(m),
        )
    except Exception as e:
        logger.warning("Date range resolution failed: %s", e)
        await status_msg.edit_text(t("date_error", lang, err=str(e)[:120]))
        return

    if newest_id is None:
        await status_msg.edit_text(t("date_none", lang, label=label_for_status))
        return

    # Parse trailing flags like /scrape does
    include_audio = False
    send_as_file = True
    include_images = False
    combined_audio = False
    chronological = (get_setting("chronological_order") == "oldest_first")
    for arg in extra_args:
        a = arg.lower()
        if a == "audio":
            include_audio = True
        elif a in ("file", "txt"):
            send_as_file = True
        elif a == "inline":
            send_as_file = False
        elif a in ("images", "img"):
            include_images = True
        elif a == "combined":
            combined_audio = True
        elif a in ("oldest-first", "oldest", "--oldest-first"):
            chronological = True
        elif a in ("newest-first", "newest", "--newest-first"):
            chronological = False

    voice = _get_voice()
    rate = _get_speed()

    desc = t(
        "date_found", lang,
        label=label_for_status, oldest=oldest_id, newest=newest_id,
    )
    flags = []
    if not send_as_file:
        flags.append("inline")
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    if include_images:
        flags.append("images")
    flag_str = (" + " + ", ".join(flags)) if flags else ""
    await status_msg.edit_text(desc + flag_str)

    cancel_event = asyncio.Event()
    task = asyncio.create_task(
        _run_job(
            chat_id=chat_id,
            bot=context.bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=False,
            use_post_ids=True,
            use_from_title=False,
            count=newest_id - oldest_id + 1,
            start_post_id=newest_id,
            end_post_id=oldest_id,
            include_audio=include_audio,
            include_images=include_images,
            send_as_file=send_as_file,
            combined_audio=combined_audio,
            voice=voice,
            rate=rate,
            lang=lang,
            chronological=chronological,
        )
    )
    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def cmd_today(update, context):
    today = _local_today()
    await _scrape_date_range(
        update, context, today, today,
        extra_args=context.args or [],
        label_for_status=t("date_label_today", _get_lang()),
    )


async def cmd_yesterday(update, context):
    yesterday = _local_today() - timedelta(days=1)
    await _scrape_date_range(
        update, context, yesterday, yesterday,
        extra_args=context.args or [],
        label_for_status=t("date_label_yesterday", _get_lang()),
    )


async def cmd_thisweek(update, context):
    end = _local_today()
    start = end - timedelta(days=6)
    await _scrape_date_range(
        update, context, start, end,
        extra_args=context.args or [],
        label_for_status=t("date_label_thisweek", _get_lang()),
    )


async def cmd_since(update, context):
    """/since YYYY-MM-DD [flags] — everything from the given date forward."""
    args = context.args or []
    lang = _get_lang()
    if not args:
        await update.message.reply_text(t("since_usage", lang))
        return
    raw = args[0]
    try:
        start = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(t("since_bad_date", lang))
        return
    end = _local_today()
    if start > end:
        await update.message.reply_text(t("since_future", lang))
        return
    await _scrape_date_range(
        update, context, start, end,
        extra_args=args[1:],
        label_for_status=t("date_label_since", lang, date=raw),
    )
