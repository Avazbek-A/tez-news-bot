"""The scrape job runner + title-anchor confirmation.

`_run_job` is the heart of the bot: it drives the pipeline and all
delivery, records history + metrics, and is launched as a background task
by /scrape, the /scrape menu, the date shortcuts, and auto-scrape. It
depends only on `common` (shared state) plus the pipeline/delivery layers
— never on the other command modules — so it sits just above `common` in
the dependency graph with nothing importing back into it from below.
"""
import asyncio
import logging
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from spot_bot.config import TTS_RATE, MAX_SCRAPE_COUNT
from spot_bot.settings import get_setting, remember_delivered
from spot_bot.translations import t
from spot_bot.pipeline import run_pipeline
from spot_bot.delivery.telegram_sender import (
    send_articles_as_text,
    send_articles_as_file,
    send_article_images,
    send_voice_messages,
    send_combined_voice,
)
from spot_bot.audio.tts_generator import cleanup_audio_files
from spot_bot.scrapers.telegram_channel import (
    find_post_id_by_title,
    _post_first_line,
)
from spot_bot import history_db
from spot_bot.alerts import evaluate_scrape_health
from spot_bot.commands.common import (
    _running_jobs,
    _pending_confirmations,
    CONFIRM_TIMEOUT,
    encode_next_batch_flags,
    next_batch_keyboard,
)

logger = logging.getLogger(__name__)


async def _run_job(*, chat_id, bot, status_msg, cancel_event,
                   use_range, use_post_ids=False, use_from_title=False,
                   count=20,
                   start_offset=None, end_offset=None,
                   start_post_id=None, end_post_id=None,
                   from_title=None, from_count=None,
                   include_audio=False, include_images=False,
                   send_as_file=True, combined_audio=False,
                   voice=None, rate=TTS_RATE, lang="en",
                   chronological=False, translate_to=None,
                   include_seen=False):
    """Background task that runs the full pipeline + delivery."""
    result = None
    run_started = time.monotonic()
    run_ok = True
    run_error = None

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
            chronological=chronological,
            translate_to=translate_to,
            include_seen=include_seen,
        )
        if use_from_title:
            # Two-stage flow: resolve title at the bot layer, ask user to
            # confirm via inline buttons, then call the pipeline with the
            # confirmed anchor ID via the post-ID forward path.
            target_count = from_count or 50
            await status_msg.edit_text(
                t("from_title_searching", lang, title=from_title)
            )

            channel_url = get_setting("channel_url")
            anchor_id, anchor_post = await find_post_id_by_title(
                from_title,
                channel_url=channel_url,
                max_search=2000,
                cancel_event=cancel_event,
                progress_callback=progress_callback,
            )
            if anchor_id is None:
                await status_msg.edit_text(
                    t("from_title_not_found", lang, title=from_title)
                )
                return

            preview = _post_first_line(anchor_post) if anchor_post else ""
            date_str = (anchor_post or {}).get("date", "?")

            confirmed = await _ask_anchor_confirmation(
                bot=bot,
                chat_id=chat_id,
                anchor_id=anchor_id,
                preview=preview,
                date_str=date_str,
                count=target_count,
                lang=lang,
                cancel_event=cancel_event,
            )
            if confirmed is None:
                # Timed out
                await status_msg.edit_text(t("confirm_timeout", lang))
                return
            if not confirmed:
                await status_msg.edit_text(t("confirm_cancelled", lang))
                return

            # User confirmed — proceed with the post-ID forward scrape.
            await status_msg.edit_text(
                t("from_title_proceeding", lang, count=target_count)
            )
            pipeline_kwargs["forward_anchor_id"] = anchor_id
            pipeline_kwargs["from_count"] = target_count
        elif use_post_ids:
            pipeline_kwargs["start_post_id"] = start_post_id
            pipeline_kwargs["end_post_id"] = end_post_id
        elif use_range:
            pipeline_kwargs["start_offset"] = start_offset
            pipeline_kwargs["end_offset"] = end_offset
        else:
            pipeline_kwargs["count"] = count

        result = await run_pipeline(**pipeline_kwargs)

        if use_from_title and result.title_not_found:
            await status_msg.edit_text(
                t("from_title_not_found", lang, title=from_title)
            )
            return

        if not result.articles:
            # If everything was intentionally filtered, say so rather than
            # a bare "nothing found" — otherwise skip-seen/mute looks like a
            # broken scrape.
            extra = []
            if result.skipped_seen_count:
                extra.append(t("no_articles_skipped_seen", lang,
                               n=result.skipped_seen_count))
            if result.muted_count:
                extra.append(t("no_articles_muted", lang, n=result.muted_count))
            msg = t("no_articles", lang)
            if extra:
                msg += "\n" + " ".join(extra)
            await status_msg.edit_text(msg)
            return

        # When title-anchored, send a SEPARATE message announcing the
        # matched anchor article + its post ID. Stays in the chat history
        # alongside the deliverables instead of being overwritten by later
        # status edits.
        if use_from_title and result.matched_title_preview:
            try:
                await bot.send_message(
                    chat_id,
                    t("from_title_anchor", lang,
                      anchor_id=result.matched_post_id,
                      preview=result.matched_title_preview),
                )
            except Exception:
                pass

        await status_msg.edit_text(
            t("sending_articles", lang, count=len(result.articles))
        )

        # Image placement strategy:
        # - inline text mode  → embed albums under each article's text
        # - file mode + individual audio → embed albums under each voice
        # - file/combined modes → flattened album batch at the end
        text_inline_images = include_images and not send_as_file
        audio_inline_images = (
            include_images and include_audio and not combined_audio
            and send_as_file
        )
        images_handled_inline = text_inline_images or audio_inline_images

        # Send text — as file or inline messages
        if send_as_file:
            await send_articles_as_file(bot, chat_id, result.articles)
        else:
            await send_articles_as_text(
                bot, chat_id, result.articles,
                bookmark_label=t("bookmark_save_btn", lang),
                share_label=t("share_btn", lang),
                inline_images=text_inline_images,
            )

        # Send images now ONLY if not embedded inline above. The flattened
        # album path is used for file mode and combined-voice mode, where
        # there's no per-article message to attach images to.
        images_sent = 0
        if include_images and not images_handled_inline:
            await status_msg.edit_text(t("sending_images", lang))
            images_sent = await send_article_images(
                bot, chat_id, result.articles
            )
        elif include_images:
            # Approximation; inline senders don't return a count.
            images_sent = sum(
                len(a.get("images") or []) for a in result.articles
            )

        # Send audio as Telegram voice messages (mobile gets native speed
        # control, waveform, and 1x/1.5x/2x playback). MP3 -> OGG/Opus
        # conversion happens inside the senders via ffmpeg.
        audio_sent = 0
        if include_audio and result.audio_results:
            async def _voice_status(text):
                try:
                    await status_msg.edit_text(text)
                except Exception:
                    pass

            if combined_audio:
                await status_msg.edit_text(t("combining_audio", lang))
                audio_sent = await send_combined_voice(
                    bot, chat_id, result.audio_results,
                    status_callback=_voice_status,
                    lang=lang,
                )
            else:
                await status_msg.edit_text(t("sending_audio", lang))
                audio_sent = await send_voice_messages(
                    bot, chat_id, result.audio_results,
                    inline_images=audio_inline_images,
                )

        # Build the structured delivery card. New in Phase 15:
        # uses delivery_card / delivery_line_* / delivery_next_batch
        # translation keys for a clean two-section layout.
        line_keys = ["delivery_line_articles"]
        line_args = [{"n": len(result.articles)}]
        if include_audio:
            line_keys.append("delivery_line_audio")
            line_args.append({"n": audio_sent})
        if include_images:
            line_keys.append("delivery_line_images")
            line_args.append({"n": images_sent})
        # Surface intentional filtering so a dropped post is never silent.
        if result.skipped_seen_count:
            line_keys.append("delivery_line_skipped_seen")
            line_args.append({"n": result.skipped_seen_count})
        if result.muted_count:
            line_keys.append("delivery_line_muted")
            line_args.append({"n": result.muted_count})
        body_lines = [
            t(k, lang, **a) for k, a in zip(line_keys, line_args)
        ]
        # A network-truncated scrape is flagged so a short batch isn't
        # mistaken for the full request (durable, unlike the transient
        # progress warning).
        if result.partial:
            body_lines.append(t("delivery_line_partial", lang))
        summary_block = "\n".join(body_lines)

        # Extract post ID range from articles for "next batch" hint
        post_ids = []
        for a in result.articles:
            if a.get("id"):
                pid = a["id"].split("/")[-1] if "/" in a.get("id", "") else None
                if pid and pid.isdigit():
                    post_ids.append(int(pid))

        # Reading log: record what we just delivered so /unread can compare
        # against the latest post in the channel.
        try:
            remember_delivered(post_ids)
        except Exception as e:
            logger.warning("[reading-log] failed to record delivered IDs: %s", e)

        # History DB: index article titles + bodies for /find searches and
        # for /stats analytics. Best-effort — never blocks delivery.
        try:
            history_db.record_articles(result.articles)
            # If audio was generated, record per-article durations so
            # /stats can sum them.
            if result.audio_results:
                from spot_bot.audio.voice import get_audio_duration
                for article, audio_path in result.audio_results:
                    if not audio_path:
                        continue
                    try:
                        dur = await get_audio_duration(audio_path)
                        if dur > 0:
                            history_db.update_audio_duration(
                                article.get("id", ""), dur,
                            )
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("[history-db] record_articles failed: %s", e)

        # Render and send the delivery card. The card is a single
        # well-formatted block with sections so the user gets a clear
        # "what just happened" at a glance.
        if post_ids:
            newest_id = max(post_ids)
            oldest_id = min(post_ids)
            card = t("delivery_card", lang,
                     summary=summary_block,
                     oldest=oldest_id,
                     newest=newest_id,
                     next_batch="")
        else:
            newest_id = oldest_id = None
            card = t("delivery_card", lang,
                     summary=summary_block,
                     oldest="?",
                     newest="?",
                     next_batch="")

        try:
            await status_msg.edit_text(card)
        except Exception:
            try:
                await bot.send_message(chat_id, card)
            except Exception:
                pass

        # One-tap "next batch" button as the LAST message, so the user
        # doesn't scroll up past the delivered articles to continue. It
        # repeats this scrape's format over the next FORWARD (newer) ID
        # window — i.e. the posts just after the ones delivered.
        #
        # Window vs. label:
        # - The ID *span* of this batch (newest-oldest) is what we step
        #   forward by — it's the best proxy for "fetch a similar amount,"
        #   accounting for gaps and posts the filters dropped. The scraper
        #   naturally clamps to whatever actually exists, so overshooting
        #   past the current latest is harmless.
        # - The button *label* shows how many articles were actually
        #   delivered this run (not the raw span, which can be much larger
        #   after muting/skip-seen). So you got 12 → the button says "12",
        #   not "50".
        if newest_id is not None:
            id_span = min(MAX_SCRAPE_COUNT, max(1, newest_id - oldest_id + 1))
            nb_start = newest_id + id_span   # newest id of the next batch
            nb_end = newest_id + 1           # just newer than what we got
            label_n = len(result.articles) or id_span
            flags = encode_next_batch_flags(
                include_audio=include_audio,
                combined_audio=combined_audio,
                include_images=include_images,
                send_as_file=send_as_file,
                include_seen=include_seen,
            )
            try:
                await bot.send_message(
                    chat_id,
                    t("next_batch_prompt", lang, n=label_n),
                    reply_markup=next_batch_keyboard(
                        nb_start, nb_end, label_n, flags, lang,
                    ),
                )
            except Exception:
                pass

    except asyncio.CancelledError:
        # User cancellation isn't a failure; don't flag the run as errored.
        try:
            await status_msg.edit_text(t("cancelled", lang))
        except Exception:
            pass

    except Exception as e:
        run_ok = False
        run_error = repr(e)
        try:
            await status_msg.edit_text(t("error", lang, e=e))
        except Exception:
            pass

    finally:
        # Cleanup
        if result and result.audio_results:
            cleanup_audio_files(result.audio_results, None)
        _running_jobs.pop(chat_id, None)

        # Operational metrics: one tiny SQLite row per run (best-effort).
        # Derived entirely from `result` so it's robust on early returns.
        try:
            if result is not None:
                n_articles = len(result.articles)
                n_audio = sum(1 for _, p in result.audio_results if p)
                n_images = sum(
                    len(a.get("images") or []) for a in result.articles
                )
                history_db.record_run(
                    articles=n_articles,
                    skipped_seen=result.skipped_seen_count,
                    muted=result.muted_count,
                    audio=n_audio,
                    images=n_images,
                    partial=result.partial,
                    duration_ms=int((time.monotonic() - run_started) * 1000),
                    ok=run_ok,
                    error=run_error,
                )
            else:
                # Errored before producing a result — still record the run.
                history_db.record_run(
                    duration_ms=int((time.monotonic() - run_started) * 1000),
                    ok=run_ok,
                    error=run_error,
                )
        except Exception as e:
            logger.warning("[metrics] record_run failed: %s", e)

        # Operational alerting: surface scraper breakage / sustained errors
        # so the operator hears about it before the client does.
        latest_mode = not (use_range or use_post_ids or use_from_title)
        await evaluate_scrape_health(
            bot, result=result, run_ok=run_ok,
            latest_mode=latest_mode, requested_count=count,
        )


# ---------------------------------------------------------------------------
# Anchor confirmation (used by /scrape from "<title>" mode)
# ---------------------------------------------------------------------------

async def _ask_anchor_confirmation(*, bot, chat_id, anchor_id, preview,
                                   date_str, count, lang, cancel_event):
    """Send an inline-keyboard confirmation message and wait for user input.

    Returns True if confirmed, False if cancelled, or None if timed out.
    """
    confirm_event = asyncio.Event()
    decision = {"yes": False}

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t("confirm_yes_btn", lang),
            callback_data="anchor_confirm_yes",
        ),
        InlineKeyboardButton(
            t("confirm_no_btn", lang),
            callback_data="anchor_confirm_no",
        ),
    ]])

    confirm_msg = await bot.send_message(
        chat_id,
        t("confirm_anchor", lang,
          anchor_id=anchor_id,
          preview=preview or "—",
          date=date_str,
          count=count),
        reply_markup=keyboard,
    )

    _pending_confirmations[chat_id] = {
        "event": confirm_event,
        "decision": decision,
        "msg_id": confirm_msg.message_id,
    }

    try:
        wait_task = asyncio.create_task(confirm_event.wait())
        cancel_task = None
        if cancel_event is not None:
            async def _cancel_watcher():
                while not cancel_event.is_set():
                    await asyncio.sleep(0.5)
            cancel_task = asyncio.create_task(_cancel_watcher())

        tasks = [wait_task] + ([cancel_task] if cancel_task else [])
        done, pending = await asyncio.wait(
            tasks,
            timeout=CONFIRM_TIMEOUT,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t_ in pending:
            t_.cancel()

        if cancel_event is not None and cancel_event.is_set():
            return False
        if not confirm_event.is_set():
            # Timed out — strip the buttons so the user knows it expired
            try:
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=confirm_msg.message_id,
                    reply_markup=None,
                )
            except Exception:
                pass
            return None

        return decision["yes"]
    finally:
        _pending_confirmations.pop(chat_id, None)


async def _handle_anchor_confirmation(update: Update,
                                      context: ContextTypes.DEFAULT_TYPE):
    """CallbackQueryHandler: routes Confirm/Cancel button clicks back to
    the waiting _ask_anchor_confirmation coroutine."""
    query = update.callback_query
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    data = query.data or ""

    pending = _pending_confirmations.get(chat_id)
    if not pending:
        # Stale button (job already ended) — acknowledge and silently strip
        try:
            await query.answer()
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    decision_yes = data == "anchor_confirm_yes"
    pending["decision"]["yes"] = decision_yes
    pending["event"].set()

    # Acknowledge the button press and remove the keyboard so the user
    # can't double-click.
    try:
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
