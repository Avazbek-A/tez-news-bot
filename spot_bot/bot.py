import asyncio
import logging
import re
import shlex
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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
from spot_bot.settings import (
    get_setting, set_setting,
    remember_delivered, add_bookmark, remove_bookmark, get_bookmarks,
    get_sources, add_source, remove_source,
)
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
    find_post_ids_for_date_range,
    _post_first_line,
)
from datetime import datetime, timedelta, timezone
from spot_bot.observability import start_heartbeat_task
from spot_bot import history_db


_RANGE_PATTERN = re.compile(r"^(\d+)-(\d+)$")

# Active jobs per chat — allows /cancel to work
_running_jobs = {}

# Pending confirmation requests for title-anchored scrapes.
# Keyed by chat_id. Value: dict with keys:
#   "event": asyncio.Event signaling user has decided
#   "decision": dict with key "yes" set to True/False
#   "msg_id": id of the message holding the inline buttons (so we can
#             remove the buttons once the decision is made)
_pending_confirmations = {}

# How long to wait for the user to click Confirm/Cancel (seconds)
CONFIRM_TIMEOUT = 300

# Pending /scrape menu state per chat. Keyed by chat_id, value is a config
# dict {"count": int, "format": str, "order": str}. Cleared when the user
# hits Start, hits Cancel, or the menu falls out of context.
_pending_scrape_configs = {}


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

    # No args → show the inline-keyboard configuration menu and stop here.
    # The menu's Start button re-enters this command with synthesized args.
    if not (context.args or []):
        await _show_scrape_menu(update, context, chat_id, lang)
        return

    # Parse args
    args = context.args or []
    count = DEFAULT_SCRAPE_COUNT
    start_offset = None
    end_offset = None
    start_post_id = None
    end_post_id = None
    from_title = None
    from_count = None
    include_audio = False
    send_as_file = True
    include_images = False
    combined_audio = False
    chronological = (get_setting("chronological_order") == "oldest_first")
    translate_override = None  # set by 'translate=<lang>' flag

    # Special syntax: /scrape from "<title>" [count] [flags...]
    # We re-parse the raw message text with shlex so the quoted title stays
    # intact regardless of whitespace inside it.
    raw_text = update.message.text or ""
    cmd_match = re.match(r"^/[A-Za-z_]+(?:@\w+)?\s*", raw_text)
    raw_args_str = raw_text[cmd_match.end():] if cmd_match else raw_text
    if raw_args_str.lstrip().lower().startswith("from"):
        try:
            tokens = shlex.split(raw_args_str)
        except ValueError:
            await update.message.reply_text(t("from_title_quotes", lang))
            return
        if tokens and tokens[0].lower() == "from":
            if len(tokens) < 2 or not tokens[1].strip():
                await update.message.reply_text(t("from_title_missing", lang))
                return
            from_title = tokens[1]
            # Everything after the title is flags / count
            args = tokens[2:]

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
            if from_title:
                from_count = min(int(arg), MAX_SCRAPE_COUNT)
            else:
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
        elif arg.lower() in ("--oldest-first", "oldest-first", "oldest"):
            chronological = True
        elif arg.lower() in ("--newest-first", "newest-first", "newest"):
            chronological = False
        elif arg.lower().startswith("translate=") or arg.lower().startswith("to="):
            value = arg.split("=", 1)[1].strip().lower()
            if value in _TRANSLATE_LANGS or value in ("off", "none"):
                translate_override = (
                    None if value in ("off", "none") else value
                )

    voice = _get_voice()
    rate = _get_speed()
    use_range = start_offset is not None and end_offset is not None
    use_post_ids = start_post_id is not None and end_post_id is not None
    use_from_title = from_title is not None
    if use_from_title and from_count is None:
        from_count = 50

    # Build description for status message
    if use_from_title:
        title_preview = from_title if len(from_title) <= 40 else from_title[:40] + "…"
        desc = f'from "{title_preview}" × {from_count}'
    elif use_post_ids:
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
            use_from_title=use_from_title,
            count=count,
            start_offset=start_offset,
            end_offset=end_offset,
            start_post_id=start_post_id,
            end_post_id=end_post_id,
            from_title=from_title,
            from_count=from_count,
            include_audio=include_audio,
            include_images=include_images,
            send_as_file=send_as_file,
            combined_audio=combined_audio,
            voice=voice,
            rate=rate,
            lang=lang,
            chronological=chronological,
            translate_to=translate_override,
        )
    )

    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


async def _run_job(*, chat_id, bot, status_msg, cancel_event,
                   use_range, use_post_ids=False, use_from_title=False,
                   count=20,
                   start_offset=None, end_offset=None,
                   start_post_id=None, end_post_id=None,
                   from_title=None, from_count=None,
                   include_audio=False, include_images=False,
                   send_as_file=True, combined_audio=False,
                   voice=None, rate=TTS_RATE, lang="en",
                   chronological=False, translate_to=None):
    """Background task that runs the full pipeline + delivery."""
    result = None

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
            await status_msg.edit_text(t("no_articles", lang))
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

        # Always show the final summary as the (overwritten) status message,
        # then send the post ID range as a SEPARATE persistent message so
        # the IDs stay visible in chat without having to open the .txt file.
        await status_msg.edit_text(summary)

        if post_ids:
            newest_id = max(post_ids)
            oldest_id = min(post_ids)
            range_size = newest_id - oldest_id
            range_msg = t("posts_range", lang,
                          oldest=oldest_id, newest=newest_id)
            if range_size > 0:
                range_msg += "\n" + t("next_batch", lang,
                                      start=newest_id,
                                      end=newest_id + range_size)
            try:
                await bot.send_message(chat_id, range_msg)
            except Exception:
                pass

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
            cleanup_audio_files(result.audio_results, None)
        _running_jobs.pop(chat_id, None)


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


# ---------------------------------------------------------------------------
# /scrape inline-keyboard menu (shown when /scrape is invoked with no args)
# ---------------------------------------------------------------------------

_MENU_DEFAULT_CONFIG = {"count": 25, "format": "text", "order": "newest"}
_MENU_COUNTS = (10, 25, 50, 100)
_MENU_FORMATS = ("text", "audio", "combined")
_MENU_ORDERS = ("newest", "oldest")


def _build_scrape_menu_keyboard(config, lang):
    """Construct the inline keyboard for the /scrape config menu, with the
    currently-selected option in each row marked by a leading ✓."""

    def opt(label_key_or_text, key, value):
        # label_key_or_text can be either a translation key or literal text
        # (used for raw numbers like 10/25/50/100).
        label = (
            label_key_or_text
            if isinstance(label_key_or_text, (str, int)) and (
                isinstance(label_key_or_text, int)
                or not label_key_or_text.startswith("menu_")
            )
            else t(label_key_or_text, lang)
        )
        if isinstance(label, int):
            label = str(label)
        prefix = "✓ " if config.get(key) == value else ""
        return InlineKeyboardButton(
            f"{prefix}{label}",
            callback_data=f"scrape_menu_{key}_{value}",
        )

    return InlineKeyboardMarkup([
        [opt(str(c), "count", c) for c in _MENU_COUNTS],
        [
            opt("menu_format_text", "format", "text"),
            opt("menu_format_audio", "format", "audio"),
            opt("menu_format_combined", "format", "combined"),
        ],
        [
            opt("menu_order_newest", "order", "newest"),
            opt("menu_order_oldest", "order", "oldest"),
        ],
        [
            InlineKeyboardButton(
                t("menu_start", lang),
                callback_data="scrape_menu_start",
            ),
            InlineKeyboardButton(
                t("menu_cancel", lang),
                callback_data="scrape_menu_cancel",
            ),
        ],
    ])


async def _show_scrape_menu(update, context, chat_id, lang):
    """Send the /scrape configuration menu, seeded with defaults (or last
    config if the user already had one open)."""
    config = _pending_scrape_configs.get(chat_id) or dict(_MENU_DEFAULT_CONFIG)
    # Seed order from the user's persisted preference if present.
    if "order" not in config:
        config["order"] = (
            "oldest"
            if get_setting("chronological_order") == "oldest_first"
            else "newest"
        )
    _pending_scrape_configs[chat_id] = config
    keyboard = _build_scrape_menu_keyboard(config, lang)
    await update.message.reply_text(
        t("menu_configure", lang),
        reply_markup=keyboard,
    )


async def _handle_scrape_menu_callback(update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
    """Route taps on the /scrape menu inline buttons."""
    query = update.callback_query
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    lang = _get_lang()
    data = query.data or ""

    config = _pending_scrape_configs.get(chat_id)
    if config is None:
        # Stale menu (bot restarted or config evicted)
        try:
            await query.answer(t("menu_expired", lang), show_alert=False)
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    payload = data[len("scrape_menu_"):] if data.startswith("scrape_menu_") else ""

    if payload == "cancel":
        _pending_scrape_configs.pop(chat_id, None)
        try:
            await query.answer()
            await query.edit_message_text(t("menu_cancelled", lang))
        except Exception:
            pass
        return

    if payload == "start":
        # Build args list to mirror the typed command, then dispatch back
        # through cmd_scrape's existing arg-parsing branch.
        config = _pending_scrape_configs.pop(chat_id, dict(_MENU_DEFAULT_CONFIG))
        synth_args = [str(config["count"])]
        if config["format"] == "audio":
            synth_args.append("audio")
        elif config["format"] == "combined":
            synth_args.extend(["audio", "combined"])
        if config["order"] == "oldest":
            synth_args.append("oldest")
        else:
            synth_args.append("newest")

        try:
            await query.answer()
            await query.edit_message_text(
                t("menu_starting", lang, args=" ".join(synth_args))
            )
        except Exception:
            pass

        # Inject synth args into context and re-enter cmd_scrape via a
        # synthesized message-like object so it sees the updated message
        # text. Simpler: just call cmd_scrape with a faux Update — but
        # reusing cmd_scrape needs update.message.text and chat. Cleanest
        # path is to call _start_scrape_from_config directly.
        await _start_scrape_from_config(query, context, chat_id, lang, config)
        return

    # Otherwise it's a `<key>_<value>` toggle. Parse:
    parts = payload.split("_", 1)
    if len(parts) != 2:
        try:
            await query.answer()
        except Exception:
            pass
        return
    key, raw_value = parts

    if key == "count":
        try:
            value = int(raw_value)
        except ValueError:
            return
        if value in _MENU_COUNTS:
            config["count"] = value
    elif key == "format" and raw_value in _MENU_FORMATS:
        config["format"] = raw_value
    elif key == "order" and raw_value in _MENU_ORDERS:
        config["order"] = raw_value

    _pending_scrape_configs[chat_id] = config

    try:
        await query.answer()
        await query.edit_message_reply_markup(
            reply_markup=_build_scrape_menu_keyboard(config, lang)
        )
    except Exception:
        pass


async def _start_scrape_from_config(query, context, chat_id, lang, config):
    """Kick off a scrape job from the menu's config. Mirrors the relevant
    portion of cmd_scrape but without the typed-arg parsing."""

    if chat_id in _running_jobs:
        try:
            await context.bot.send_message(chat_id, t("job_running", lang))
        except Exception:
            pass
        return

    count = min(int(config["count"]), MAX_SCRAPE_COUNT)
    include_audio = config["format"] in ("audio", "combined")
    combined_audio = config["format"] == "combined"
    chronological = config["order"] == "oldest"

    voice = _get_voice()
    rate = _get_speed()

    desc = f"latest {count}"
    flags = []
    if include_audio:
        flags.append("combined audio" if combined_audio else "audio")
    flag_str = (" + " + ", ".join(flags)) if flags else ""

    status_msg = await context.bot.send_message(
        chat_id, t("starting", lang, desc=f"{desc}{flag_str}")
    )

    cancel_event = asyncio.Event()
    task = asyncio.create_task(
        _run_job(
            chat_id=chat_id,
            bot=context.bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=False,
            use_post_ids=False,
            use_from_title=False,
            count=count,
            include_audio=include_audio,
            include_images=False,
            send_as_file=True,
            combined_audio=combined_audio,
            voice=voice,
            rate=rate,
            lang=lang,
            chronological=chronological,
        )
    )
    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


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
    """/voice                        — show current
    /voice <name>                  — set the global default voice
    /voice <lang> <name>           — override the voice for one language
                                       (lang in: ru, en, uz, de, tr)
    """
    args = context.args or []
    lang = _get_lang()
    voice_list = _build_voice_list(lang)

    if not args:
        current = _get_voice()
        overrides = get_setting("voices_by_lang") or {}
        if overrides:
            current_str = current + " | per-lang: " + ", ".join(
                f"{k}={v}" for k, v in sorted(overrides.items())
            )
        else:
            current_str = current
        await update.message.reply_text(
            t("voice_current", lang, voice=current_str, voice_list=voice_list)
        )
        return

    # /voice <lang> <name> — per-language override
    if len(args) >= 2 and args[0].lower() in {"ru", "en", "uz", "de", "tr"}:
        per_lang = args[0].lower()
        name = args[1].lower()
        if name not in AVAILABLE_VOICES:
            await update.message.reply_text(
                t("voice_unknown", lang, name=name, voice_list=voice_list)
            )
            return
        overrides = dict(get_setting("voices_by_lang") or {})
        overrides[per_lang] = AVAILABLE_VOICES[name]
        set_setting("voices_by_lang", overrides)
        await update.message.reply_text(
            t("voice_set_for_lang", lang,
              lang_code=per_lang, voice=AVAILABLE_VOICES[name])
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
# /order — default chronological order for delivery
# ---------------------------------------------------------------------------

async def cmd_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()

    current = get_setting("chronological_order") or "newest_first"

    if not args:
        await update.message.reply_text(t("order_current", lang, order=current))
        return

    choice = args[0].lower()
    if choice in ("newest", "newest_first", "new"):
        new_value = "newest_first"
    elif choice in ("oldest", "oldest_first", "old", "chronological"):
        new_value = "oldest_first"
    else:
        await update.message.reply_text(t("order_unknown", lang, name=choice))
        return

    set_setting("chronological_order", new_value)
    await update.message.reply_text(t("order_set", lang, order=new_value))


# ---------------------------------------------------------------------------
# /voice_engine — choose between Edge TTS (default) and Piper TTS (local)
# ---------------------------------------------------------------------------

async def cmd_voice_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()
    current = (get_setting("voice_engine") or "edge").lower()

    if not args:
        try:
            from spot_bot.audio.piper_engine import piper_available
            piper_ready = piper_available()
        except Exception:
            piper_ready = False
        if current == "supertonic":
            await update.message.reply_text(t("voice_engine_supertonic_on", lang))
        elif current == "piper":
            if piper_ready:
                await update.message.reply_text(t("voice_engine_piper_on", lang))
            else:
                await update.message.reply_text(t("voice_engine_piper_no_model", lang))
        else:
            await update.message.reply_text(t("voice_engine_edge_on", lang))
        return

    choice = args[0].lower()
    if choice not in ("edge", "piper", "supertonic"):
        await update.message.reply_text(t("voice_engine_unknown", lang))
        return
    set_setting("voice_engine", choice)
    if choice == "supertonic":
        await update.message.reply_text(t("voice_engine_set_supertonic", lang))
    elif choice == "piper":
        try:
            from spot_bot.audio.piper_engine import piper_available
            piper_ready = piper_available()
        except Exception:
            piper_ready = False
        if piper_ready:
            await update.message.reply_text(t("voice_engine_set_piper", lang))
        else:
            await update.message.reply_text(t("voice_engine_set_piper_no_model", lang))
    else:
        await update.message.reply_text(t("voice_engine_set_edge", lang))


# ---------------------------------------------------------------------------
# /translate — set article translation target language (Phase 13)
# ---------------------------------------------------------------------------

_TRANSLATE_LANGS = {"en", "ru", "uz", "de", "tr"}


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import os as _os
    args = context.args or []
    lang = _get_lang()
    has_key = bool((_os.environ.get("GROQ_API_KEY") or "").strip())
    current = get_setting("translate_to")

    if not args:
        if current and has_key:
            await update.message.reply_text(
                t("translate_status_on", lang, target=current)
            )
        elif current:
            await update.message.reply_text(t("translate_no_key", lang))
        else:
            await update.message.reply_text(t("translate_status_off", lang))
        return

    choice = args[0].lower()
    if choice in ("off", "none", "0", "no"):
        set_setting("translate_to", None)
        await update.message.reply_text(t("translate_set_off", lang))
        return
    if choice not in _TRANSLATE_LANGS:
        await update.message.reply_text(t("translate_unknown", lang, choice=choice))
        return
    set_setting("translate_to", choice)
    if has_key:
        await update.message.reply_text(t("translate_set_on", lang, target=choice))
    else:
        await update.message.reply_text(
            t("translate_set_on_no_key", lang, target=choice)
        )


# ---------------------------------------------------------------------------
# /summarize — toggle LLM summaries via Groq free tier (Phase 8)
# ---------------------------------------------------------------------------

async def cmd_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import os as _os
    args = context.args or []
    lang = _get_lang()
    current = bool(get_setting("enable_summaries"))
    has_key = bool((_os.environ.get("GROQ_API_KEY") or "").strip())

    if not args:
        if current:
            await update.message.reply_text(
                t("summarize_status_on" if has_key else "summarize_status_no_key", lang)
            )
        else:
            await update.message.reply_text(t("summarize_status_off", lang))
        return

    choice = args[0].lower()
    if choice in ("on", "1", "yes", "true"):
        new_value = True
    elif choice in ("off", "0", "no", "false"):
        new_value = False
    else:
        await update.message.reply_text(t("summarize_unknown", lang, choice=choice))
        return

    set_setting("enable_summaries", new_value)
    if new_value and not has_key:
        await update.message.reply_text(t("summarize_set_on_no_key", lang))
    elif new_value:
        await update.message.reply_text(t("summarize_set_on", lang))
    else:
        await update.message.reply_text(t("summarize_set_off", lang))


# ---------------------------------------------------------------------------
# /quality, /topics, /dedup — smart filtering toggles (Phase 7)
# ---------------------------------------------------------------------------

async def cmd_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/quality [N] — set min cleaned-body length. /quality 0 disables."""
    args = context.args or []
    lang = _get_lang()
    if not args:
        current = int(get_setting("quality_threshold") or 0)
        if current <= 0:
            await update.message.reply_text(t("quality_off", lang))
        else:
            await update.message.reply_text(t("quality_status", lang, n=current))
        return
    try:
        n = int(args[0])
    except ValueError:
        await update.message.reply_text(t("quality_usage", lang))
        return
    if n < 0 or n > 10000:
        await update.message.reply_text(t("quality_range", lang))
        return
    set_setting("quality_threshold", n)
    if n == 0:
        await update.message.reply_text(t("quality_set_off", lang))
    else:
        await update.message.reply_text(t("quality_set_on", lang, n=n))


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/topics [keyword ...] — list, set, or clear (with `off`) topic filter."""
    args = context.args or []
    lang = _get_lang()
    current = list(get_setting("topics") or [])
    if not args:
        if not current:
            await update.message.reply_text(t("topics_off", lang))
        else:
            await update.message.reply_text(
                t("topics_status", lang, list=", ".join(current))
            )
        return
    if args[0].lower() in ("off", "clear", "none"):
        set_setting("topics", [])
        await update.message.reply_text(t("topics_set_off", lang))
        return
    # Replace topics with the given list
    new_topics = [a.strip().lower() for a in args if a.strip()]
    set_setting("topics", new_topics)
    await update.message.reply_text(
        t("topics_set_on", lang, list=", ".join(new_topics))
    )


async def cmd_dedup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dedup [threshold] — title-similarity threshold (0-100). 100 disables."""
    args = context.args or []
    lang = _get_lang()
    if not args:
        current = int(get_setting("dup_threshold") or 100)
        if current >= 100:
            await update.message.reply_text(t("dedup_off", lang))
        else:
            await update.message.reply_text(t("dedup_status", lang, n=current))
        return
    try:
        n = int(args[0])
    except ValueError:
        await update.message.reply_text(t("dedup_usage", lang))
        return
    if n < 0 or n > 100:
        await update.message.reply_text(t("dedup_range", lang))
        return
    set_setting("dup_threshold", n)
    if n >= 100:
        await update.message.reply_text(t("dedup_set_off", lang))
    else:
        await update.message.reply_text(t("dedup_set_on", lang, n=n))


# ---------------------------------------------------------------------------
# /today, /yesterday, /thisweek, /since — date-based scrape shortcuts
# ---------------------------------------------------------------------------

# Default user timezone (Tashkent). Phase 5 will make this configurable.
_DEFAULT_TZ_OFFSET_HOURS = 5  # Asia/Tashkent (UTC+5)


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


# ---------------------------------------------------------------------------
# /ads — toggle whether ads + sponsored content are kept in output
# ---------------------------------------------------------------------------

async def cmd_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    lang = _get_lang()
    current = bool(get_setting("include_ads"))

    if not args:
        await update.message.reply_text(
            t("ads_status_on" if current else "ads_status_off", lang)
        )
        return

    choice = args[0].lower()
    if choice in ("on", "1", "yes", "include", "true"):
        new_value = True
    elif choice in ("off", "0", "no", "exclude", "false"):
        new_value = False
    else:
        await update.message.reply_text(t("ads_unknown", lang, choice=choice))
        return

    set_setting("include_ads", new_value)
    await update.message.reply_text(
        t("ads_set_on" if new_value else "ads_set_off", lang)
    )


# ---------------------------------------------------------------------------
# Audio resume markers
# ---------------------------------------------------------------------------

async def _handle_resume_mark(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    """Tap on the "📍 Mark here" button below a voice message — saves the
    chat_id + message_id so /resume can scroll back to it later."""
    import time as _time
    query = update.callback_query
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    msg_id = query.message.message_id if query.message else None
    lang = _get_lang()
    if msg_id is None:
        try:
            await query.answer()
        except Exception:
            pass
        return
    set_setting("resume_marker", {
        "chat_id": chat_id,
        "msg_id": msg_id,
        "marked_at": int(_time.time()),
    })
    try:
        await query.answer(t("resume_marked_toast", lang), show_alert=False)
    except Exception:
        pass


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply pointing at the most recently marked voice message."""
    lang = _get_lang()
    marker = get_setting("resume_marker") or {}
    if not marker or not marker.get("msg_id"):
        await update.message.reply_text(t("resume_none", lang))
        return

    chat_id = update.effective_chat.id
    if marker.get("chat_id") != chat_id:
        # Marker was set in a different chat (shouldn't happen for personal
        # bot but safe-guard anyway). Treat as none.
        await update.message.reply_text(t("resume_none", lang))
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("resume_pointer", lang),
            reply_to_message_id=marker["msg_id"],
            disable_notification=True,
        )
    except Exception as e:
        # The marked message may have been deleted from chat history.
        logger.warning("[resume] reply failed: %s", e)
        await update.message.reply_text(
            t("resume_lost", lang)
        )


# ---------------------------------------------------------------------------
# /stats — analytics from history_db
# ---------------------------------------------------------------------------

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import time as _time
    lang = _get_lang()
    now = int(_time.time())
    week_ago = now - 7 * 86400

    s_total = history_db.stats(since_unix=0)
    s_week = history_db.stats(since_unix=week_ago)

    bookmarks = get_bookmarks()
    n_bookmarks = len(bookmarks)

    days_active = 0
    if s_total["first_delivery"] > 0:
        days_active = max(1, (now - s_total["first_delivery"]) // 86400)

    total_audio_min = int(s_total["total_audio_sec"] // 60)
    week_audio_min = int(s_week["total_audio_sec"] // 60)

    text = t(
        "stats_body", lang,
        articles_week=s_week["n_articles"],
        articles_total=s_total["n_articles"],
        audio_week=week_audio_min,
        audio_total=total_audio_min,
        bookmarks=n_bookmarks,
        days_active=days_active,
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# /find <query> — search delivered articles
# ---------------------------------------------------------------------------

async def cmd_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    args = context.args or []
    if not args:
        await update.message.reply_text(t("find_usage", lang))
        return
    query = " ".join(args).strip()
    matches = history_db.find(query, limit=20)
    if not matches:
        await update.message.reply_text(t("find_none", lang, query=query))
        return

    lines = [t("find_header", lang, n=len(matches), query=query)]
    for m in matches:
        title = (m.get("title") or m.get("body_head") or "")[:80]
        date = m.get("date_iso") or "?"
        pid = m.get("post_id") or 0
        if pid:
            lines.append(f"#{pid}  {date}  {title}")
            lines.append(f"  → /scrape {pid}-{pid}")
        else:
            lines.append(f"{date}  {title}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# /unread — show how many new articles since last delivery
# ---------------------------------------------------------------------------

async def cmd_unread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    delivered = get_setting("delivered_post_ids") or []
    if not delivered:
        await update.message.reply_text(t("unread_empty", lang))
        return

    last_seen = max(delivered)

    # Probe the channel's current latest post ID.
    from spot_bot.scrapers.telegram_channel import (
        async_playwright, _get_latest_post_id,
    )
    channel_url = get_setting("channel_url")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                ctx = await browser.new_context()
                page = await ctx.new_page()
                await page.goto(channel_url)
                await page.wait_for_selector(
                    ".tgme_widget_message", state="visible", timeout=10000,
                )
                latest_id = await _get_latest_post_id(page)
            finally:
                await browser.close()
    except Exception as e:
        await update.message.reply_text(t("unread_error", lang, err=str(e)[:120]))
        return

    if latest_id is None:
        await update.message.reply_text(t("unread_error", lang, err="no posts"))
        return

    if latest_id <= last_seen:
        await update.message.reply_text(t("unread_none", lang, last=last_seen))
        return

    new_count = latest_id - last_seen
    await update.message.reply_text(
        t("unread_count", lang,
          count=new_count, last=last_seen, latest=latest_id)
    )


# ---------------------------------------------------------------------------
# /bookmarks — list saved articles
# ---------------------------------------------------------------------------

async def cmd_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bookmarks [tag] — list saved articles, optionally filtered by tag."""
    lang = _get_lang()
    args = context.args or []
    tag_filter = args[0].strip().lower() if args else None

    items = get_bookmarks()
    if tag_filter:
        items = [b for b in items if tag_filter in (b.get("tags") or [])]
    if not items:
        if tag_filter:
            await update.message.reply_text(
                t("bookmarks_empty_tag", lang, tag=tag_filter)
            )
        else:
            await update.message.reply_text(t("bookmarks_empty", lang))
        return

    items.sort(key=lambda x: int(x.get("id", 0)), reverse=True)
    if tag_filter:
        lines = [t("bookmarks_header_tag", lang, n=len(items), tag=tag_filter)]
    else:
        lines = [t("bookmarks_header", lang, n=len(items))]
    for it in items:
        pid = int(it.get("id", 0))
        tags = it.get("tags") or []
        tag_str = " " + ", ".join(f"#{tg}" for tg in tags) if tags else ""
        lines.append(f"#{pid}{tag_str}  ·  /scrape {pid}-{pid}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    await update.message.reply_text(text)


async def cmd_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bookmark <id> [tags...] — save (or update tags on) a post ID."""
    args = context.args or []
    lang = _get_lang()
    if not args or not args[0].lstrip("#").isdigit():
        await update.message.reply_text(t("bookmark_usage", lang))
        return
    pid = int(args[0].lstrip("#"))
    tags = [a.strip().lower() for a in args[1:] if a.strip()]
    add_bookmark(pid, tags=tags)
    if tags:
        await update.message.reply_text(
            t("bookmark_added_tags", lang, id=pid, tags=", ".join(tags))
        )
    else:
        await update.message.reply_text(t("bookmark_added", lang, id=pid))


# ---------------------------------------------------------------------------
# /unbookmark <id> — remove a bookmark
# ---------------------------------------------------------------------------

async def cmd_unbookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    args = context.args or []
    if not args or not args[0].lstrip("#").isdigit():
        await update.message.reply_text(t("unbookmark_usage", lang))
        return
    pid = int(args[0].lstrip("#"))
    if remove_bookmark(pid):
        await update.message.reply_text(t("unbookmark_removed", lang, id=pid))
    else:
        await update.message.reply_text(t("unbookmark_not_found", lang, id=pid))


async def _handle_share_callback(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    """Tap 📤 Share — sends a forwardable message containing a clean
    text preview of the article + its public Telegram link, suitable
    for forwarding to another chat.
    """
    query = update.callback_query
    lang = _get_lang()
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    data = query.data or ""
    if not data.startswith("share_"):
        return
    raw = data[len("share_"):]
    if not raw.isdigit():
        try:
            await query.answer()
        except Exception:
            pass
        return
    pid = int(raw)

    # Look up the article from history; if missing, fall back to the
    # parent message's text.
    matches = history_db.find(str(pid), limit=1)
    if not matches:
        # Try the parent message's text
        title_preview = (query.message.text or "")[:200] if query.message else ""
        body_preview = ""
    else:
        m = matches[0]
        title_preview = m.get("title") or ""
        body_preview = (m.get("body_head") or "")[:280]

    # Build a share-friendly message with the public Telegram permalink.
    sources = get_sources()
    source_url = sources[0]["url"] if sources else "https://t.me/s/spotuz"
    # Convert https://t.me/s/<channel> to https://t.me/<channel>/<post_id>
    public_link = source_url.replace("/s/", "/").rstrip("/") + f"/{pid}"

    parts = []
    if title_preview:
        parts.append(f"<b>{_html_escape(title_preview)}</b>")
    if body_preview:
        parts.append(_html_escape(body_preview))
    parts.append(public_link)
    text = "\n\n".join(parts)

    try:
        await query.answer()
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
    except Exception as e:
        logger.warning("[share] send failed: %s", e)
        try:
            await query.answer(f"Error: {e}", show_alert=True)
        except Exception:
            pass


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


async def _handle_bookmark_callback(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
    """Tap on a "🔖 Save" inline button under an article message."""
    query = update.callback_query
    lang = _get_lang()
    data = query.data or ""

    if not data.startswith("bookmark_"):
        return
    raw = data[len("bookmark_"):]
    if not raw.isdigit():
        try:
            await query.answer()
        except Exception:
            pass
        return
    pid = int(raw)

    try:
        add_bookmark(pid)
        await query.answer(t("bookmark_saved_toast", lang, id=pid))
        # Update the button label so the user sees confirmation.
        new_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                t("bookmark_saved_btn", lang),
                callback_data="bookmark_done",
            ),
        ]])
        try:
            await query.edit_message_reply_markup(reply_markup=new_kb)
        except Exception:
            pass
    except Exception as e:
        try:
            await query.answer(f"Error: {e}", show_alert=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# /sources, /addsource, /removesource — multi-source management
# ---------------------------------------------------------------------------

def _slugify_source_id(label_or_url: str) -> str:
    """Build a short URL-safe id from a label or URL."""
    base = (label_or_url or "").strip().lower()
    # Strip protocol + www
    for prefix in ("https://", "http://"):
        if base.startswith(prefix):
            base = base[len(prefix):]
    if base.startswith("www."):
        base = base[4:]
    # Replace non-alphanumeric with underscores
    out = []
    for ch in base:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    slug = "".join(out).strip("_")[:32]
    return slug or "source"


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    sources = get_sources()
    if not sources:
        await update.message.reply_text(t("sources_empty", lang))
        return
    lines = [t("sources_header", lang, n=len(sources))]
    for s in sources:
        lines.append(
            f"• {s.get('id')} [{s.get('type')}] — {s.get('label') or s.get('url')}\n  {s.get('url')}"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_addsource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addsource <type> <url> [label]"""
    lang = _get_lang()
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(t("addsource_usage", lang))
        return
    stype = args[0].lower()
    url = args[1].strip()
    label = " ".join(args[2:]).strip() or url
    if stype not in ("telegram", "rss"):
        await update.message.reply_text(t("addsource_bad_type", lang))
        return
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text(t("addsource_bad_url", lang))
        return
    if stype == "telegram" and not url.startswith("https://t.me/s/"):
        await update.message.reply_text(t("addsource_bad_telegram_url", lang))
        return

    sid = _slugify_source_id(label or url)
    # Disambiguate against existing ids
    existing_ids = {s.get("id") for s in get_sources()}
    if sid in existing_ids:
        n = 2
        while f"{sid}_{n}" in existing_ids:
            n += 1
        sid = f"{sid}_{n}"

    add_source({"id": sid, "type": stype, "url": url, "label": label})
    await update.message.reply_text(t("addsource_added", lang, id=sid, label=label))


async def cmd_removesource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/removesource <id>"""
    lang = _get_lang()
    args = context.args or []
    if not args:
        await update.message.reply_text(t("removesource_usage", lang))
        return
    sid = args[0].strip()
    if remove_source(sid):
        await update.message.reply_text(t("removesource_removed", lang, id=sid))
    else:
        await update.message.reply_text(t("removesource_not_found", lang, id=sid))


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

    body = t("status", lang,
        channel=channel,
        voice=voice,
        speed=speed,
        language=lang_display,
        auto=auto_info,
        job=t("status_yes", lang) if has_job else t("status_no", lang),
        default_count=DEFAULT_SCRAPE_COUNT,
        max_count=MAX_SCRAPE_COUNT,
        max_offset=MAX_OFFSET,
    )
    keep_ads = bool(get_setting("include_ads"))
    body += "\n" + t("status_ads_on" if keep_ads else "status_ads_off", lang)
    await update.message.reply_text(body)


# ---------------------------------------------------------------------------
# /auto — scheduled auto-scrape
# ---------------------------------------------------------------------------

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


async def _post_init(app: Application):
    """Restore scheduled jobs and start observability hooks on startup."""
    config = get_setting("auto_scrape")
    if config and config.get("enabled"):
        _schedule_auto_scrape(app, config)
        logger.info(
            "Auto-scrape restored: every %d day(s), %d articles",
            config["interval_days"],
            config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
        )

    # Outbound heartbeat (no-op when HEARTBEAT_URL is unset).
    start_heartbeat_task()


async def _on_unhandled_error(update, context):
    """Forward unhandled exceptions in handlers to Sentry (if configured)
    and to logs. Without this handler, python-telegram-bot logs the
    traceback but Sentry never sees it."""
    err = context.error
    if err is None:
        return
    # Conflict errors during polling are noise we already handle elsewhere;
    # log without escalating to Sentry.
    from telegram.error import Conflict
    if isinstance(err, Conflict):
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(err)
    except Exception:
        pass
    logger.exception("[unhandled-error] %s: %s", type(err).__name__, err)


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
    app.add_handler(CommandHandler("order", cmd_order))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("auto", cmd_auto))
    app.add_handler(CommandHandler("ads", cmd_ads))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("voice_engine", cmd_voice_engine))
    app.add_handler(CommandHandler("quality", cmd_quality))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("dedup", cmd_dedup))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("yesterday", cmd_yesterday))
    app.add_handler(CommandHandler("thisweek", cmd_thisweek))
    app.add_handler(CommandHandler("since", cmd_since))
    app.add_handler(CommandHandler("find", cmd_find))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("unread", cmd_unread))
    app.add_handler(CommandHandler("bookmark", cmd_bookmark))
    app.add_handler(CommandHandler("bookmarks", cmd_bookmarks))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("unbookmark", cmd_unbookmark))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("addsource", cmd_addsource))
    app.add_handler(CommandHandler("removesource", cmd_removesource))
    app.add_handler(CallbackQueryHandler(
        _handle_anchor_confirmation,
        pattern=r"^anchor_confirm_(yes|no)$",
    ))
    app.add_handler(CallbackQueryHandler(
        _handle_scrape_menu_callback,
        pattern=r"^scrape_menu_",
    ))
    app.add_handler(CallbackQueryHandler(
        _handle_bookmark_callback,
        pattern=r"^bookmark_",
    ))
    app.add_handler(CallbackQueryHandler(
        _handle_share_callback,
        pattern=r"^share_",
    ))
    app.add_handler(CallbackQueryHandler(
        _handle_resume_mark,
        pattern=r"^resume_mark$",
    ))
    app.add_error_handler(_on_unhandled_error)

    return app
