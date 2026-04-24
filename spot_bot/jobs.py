"""Background job management: /scrape pipeline runs + scheduled auto-scrape.

Extracted from bot.py so handlers can focus on user-facing logic. The
module owns:
- `_running_jobs` (per-chat job registry used by /cancel)
- `run_job()` (background task that drives the pipeline + delivery)
- `schedule_auto_scrape()` and the JobQueue callback
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any

from telegram.ext import ContextTypes

from spot_bot.audio.tts_generator import (
    cleanup_audio_files,
    combine_audio_with_announcements,
)
from spot_bot.config import DEFAULT_AUTO_SCRAPE_COUNT, TTS_RATE
from spot_bot.delivery.telegram_sender import (
    send_article_images,
    send_articles_as_file,
    send_articles_as_text,
    send_audio_files,
    send_combined_audio,
)
from spot_bot.errors import classify_exception
from spot_bot.logging_config import new_op_id, set_op_context
from spot_bot.pipeline import run_pipeline
from spot_bot.storage import op_log, user_settings
from spot_bot.translations import t

logger = logging.getLogger(__name__)


# user_id -> {"task": Task, "cancel_event": Event, "chat_id": int}
# Keyed by user_id (not chat_id) so a single user can't run two scrapes at
# once across different chats, while distinct users in the same group
# chat can scrape in parallel. chat_id is carried in the value for
# cancel-message delivery.
running_jobs: dict[int, dict[str, Any]] = {}


async def run_job(
    *,
    chat_id: int,
    user_id: int,
    bot: Any,
    status_msg: Any,
    cancel_event: asyncio.Event,
    use_range: bool,
    use_post_ids: bool = False,
    count: int = 20,
    start_offset: int | None = None,
    end_offset: int | None = None,
    start_post_id: int | None = None,
    end_post_id: int | None = None,
    include_audio: bool = False,
    include_images: bool = False,
    include_summary: bool = False,
    send_as_file: bool = True,
    combined_audio: bool = False,
    voice: str | None = None,
    rate: str = TTS_RATE,
    lang: str = "en",
) -> None:
    """Background task that runs the full pipeline + delivery."""
    result = None
    combined_path = None
    op_id = new_op_id()
    set_op_context(op_id, user_id=user_id)
    logger.info(
        "Job start: post_ids=%s range=%s count=%s audio=%s images=%s",
        use_post_ids, use_range, count, include_audio, include_images,
    )
    await op_log.start(
        op_id, user_id, "scrape",
        {
            "use_post_ids": use_post_ids, "use_range": use_range,
            "count": count, "range": (start_post_id, end_post_id)
                if use_post_ids else (start_offset, end_offset),
            "audio": include_audio, "images": include_images,
        },
    )

    images_sent = 0
    audio_sent = 0

    try:
        async def progress_callback(text: str) -> None:
            logger.debug("progress: %s", text)
            try:
                await status_msg.edit_text(text)
            except Exception as e:
                logger.warning("Could not update status message: %s", e)

        pipeline_kwargs: dict[str, Any] = dict(
            include_audio=include_audio,
            include_images=include_images,
            include_summary=include_summary,
            voice=voice,
            rate=rate,
            lang=lang,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            user_id=user_id,
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
            await op_log.complete(op_id, 0)
            return

        await status_msg.edit_text(
            t("sending_articles", lang, count=len(result.articles))
        )

        if send_as_file:
            await send_articles_as_file(bot, chat_id, result.articles)
        else:
            await send_articles_as_text(bot, chat_id, result.articles)

        if include_images:
            await status_msg.edit_text(t("sending_images", lang))
            images_sent = await send_article_images(
                bot, chat_id, result.articles
            )

        if include_audio and result.audio_results:
            if combined_audio:
                await status_msg.edit_text(t("combining_audio", lang))
                tmpdir = tempfile.mkdtemp(prefix="spot_combined_")
                out_path = os.path.join(tmpdir, "combined.mp3")
                combined_path = await combine_audio_with_announcements(
                    result.audio_results,
                    out_path,
                    voice or "",
                    rate,
                    announcement_prefix=t("announcement_prefix", lang),
                    untitled_text=t("untitled", lang),
                )
                if combined_path:
                    await status_msg.edit_text(t("sending_combined", lang))
                    success = await send_combined_audio(
                        bot, chat_id, combined_path, len(result.articles),
                    )
                    if success:
                        audio_sent = sum(
                            1 for _, p in result.audio_results if p
                        )
                    else:
                        await status_msg.edit_text(t("combined_too_large", lang))
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
        if result.skipped_ids:
            parts.append(f"{len(result.skipped_ids)} skipped")
        if result.filtered_count:
            parts.append(
                t("filter_dropped_note", lang, n=result.filtered_count)
            )
        if include_images:
            parts.append(t("images_count", lang, n=images_sent))
        if include_audio:
            parts.append(t("audio_count", lang, n=audio_sent))
        summary = t("done_sent", lang, parts=", ".join(parts))

        post_ids = []
        for a in result.articles:
            raw_id = a.get("id", "")
            if "/" in raw_id:
                pid = raw_id.split("/")[-1]
                if pid.isdigit():
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
            # Remember highest post ID for /latest.
            await user_settings.set_value(user_id, "last_scraped_id", newest_id)

        await status_msg.edit_text(summary)
        logger.info(
            "Job complete: %d articles, %d images, %d audio, %d skipped, %d filtered",
            len(result.articles), images_sent, audio_sent,
            len(result.skipped_ids), result.filtered_count,
        )
        await op_log.complete(op_id, len(result.articles))

    except asyncio.CancelledError:
        logger.info("Job cancelled by user")
        await op_log.cancel(op_id)
        try:
            await status_msg.edit_text(t("cancelled", lang))
        except Exception as edit_err:
            logger.warning("Could not update cancellation status: %s", edit_err)

    except Exception as e:
        logger.exception("Job failed")
        user_err = classify_exception(e)
        await op_log.fail(op_id, f"{type(e).__name__}: {e}")
        try:
            await status_msg.edit_text(user_err.user_message(lang))
        except Exception as edit_err:
            logger.warning("Could not update error status: %s", edit_err)

    finally:
        if result and result.audio_results:
            cleanup_audio_files(result.audio_results, combined_path)
        running_jobs.pop(user_id, None)


# ---------------------------------------------------------------------------
# Scheduled auto-scrape
# ---------------------------------------------------------------------------


def schedule_auto_scrape(
    app: Any,  # Application is generic; we don't pin its type params here
    config: dict[str, Any] | None,
) -> None:
    """Schedule or reschedule the auto-scrape repeating job.
    `config` carries chat_id/user_id plus scrape options."""
    job_queue = app.job_queue
    if job_queue is None:
        logger.warning("job-queue extra not installed. Auto-scrape unavailable.")
        return

    user_id = (config or {}).get("user_id") or (config or {}).get("chat_id")
    name = f"auto_scrape_{user_id}" if user_id else "auto_scrape"
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()

    if not config or not config.get("enabled"):
        return

    interval_seconds = config["interval_days"] * 86400
    job_queue.run_repeating(
        callback=_auto_scrape_callback,
        interval=interval_seconds,
        first=interval_seconds,
        name=name,
        data=config,
    )


async def _auto_scrape_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue callback — runs the scheduled scrape."""
    job = context.job
    if job is None or job.data is None:
        logger.warning("Auto-scrape callback fired with no job/data")
        return
    config: dict[str, Any] = job.data  # type: ignore[assignment]
    chat_id = config["chat_id"]
    user_id = config.get("user_id", chat_id)
    bot = context.bot
    lang = await user_settings.get(user_id, "lang") or "en"

    if user_id in running_jobs:
        try:
            await bot.send_message(chat_id, t("auto_skipped", lang))
        except Exception as e:
            logger.warning("Could not notify auto-scrape skip: %s", e)
        return

    try:
        status_msg = await bot.send_message(chat_id, t("auto_starting", lang))
    except Exception as e:
        logger.warning("Could not start auto-scrape: %s", e)
        return

    cancel_event = asyncio.Event()
    voice = await user_settings.get(user_id, "voice")
    rate = await user_settings.get(user_id, "speed")

    task = asyncio.create_task(
        run_job(
            chat_id=chat_id,
            user_id=user_id,
            bot=bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=False,
            count=config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
            include_audio=config.get("include_audio", False),
            include_images=config.get("include_images", False),
            send_as_file=config.get("send_as_file", True),
            combined_audio=config.get("combined_audio", False),
            voice=voice,
            rate=rate,
            lang=lang,
        )
    )
    running_jobs[user_id] = {
        "task": task, "cancel_event": cancel_event, "chat_id": chat_id,
    }
