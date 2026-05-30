"""/scrape, its no-args inline-keyboard menu, and /cancel."""
import asyncio
import re
import shlex

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from spot_bot.config import (
    DEFAULT_SCRAPE_COUNT,
    MAX_SCRAPE_COUNT,
    MAX_OFFSET,
)
from spot_bot.settings import get_setting
from spot_bot.translations import t
from spot_bot.commands.common import (
    _RANGE_PATTERN,
    _running_jobs,
    _pending_scrape_configs,
    _TRANSLATE_LANGS,
    _get_voice,
    _get_speed,
    _get_lang,
    NEXT_BATCH_PREFIX,
    decode_next_batch_flags,
)
from spot_bot.commands.runner import _run_job


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
    include_seen = False  # set by the 'all' flag to bypass skip-seen
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
        elif arg.lower() == "all":
            include_seen = True  # re-deliver already-seen posts this run
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
            include_seen=include_seen,
        )
    )

    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}


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
# "Next batch" inline button (sent at the bottom of every delivery)
# ---------------------------------------------------------------------------

async def _handle_next_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """One tap → scrape the next older ID window, same format as the run
    that produced the button. callback_data: nb_<start>_<end>_<flags>."""
    query = update.callback_query
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    lang = _get_lang()
    data = query.data or ""
    if not data.startswith(NEXT_BATCH_PREFIX):
        return

    try:
        await query.answer()
    except Exception:
        pass

    if chat_id in _running_jobs:
        try:
            await context.bot.send_message(chat_id, t("job_running", lang))
        except Exception:
            pass
        return

    payload = data[len(NEXT_BATCH_PREFIX):]
    parts = payload.split("_")
    if len(parts) < 2:
        return
    try:
        start_id = int(parts[0])
        end_id = int(parts[1])
    except ValueError:
        return
    flags = parts[2] if len(parts) > 2 else "t"
    opts = decode_next_batch_flags(flags)

    # Disable the tapped button so it can't double-fire.
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    voice = _get_voice()
    rate = _get_speed()
    chronological = (get_setting("chronological_order") == "oldest_first")
    translate_to = get_setting("translate_to")

    status_msg = await context.bot.send_message(
        chat_id, t("starting", lang, desc=f"posts #{end_id}-#{start_id}")
    )
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
            count=start_id - end_id + 1,
            start_post_id=start_id,
            end_post_id=end_id,
            include_audio=opts["include_audio"],
            include_images=opts["include_images"],
            send_as_file=opts["send_as_file"],
            combined_audio=opts["combined_audio"],
            voice=voice,
            rate=rate,
            lang=lang,
            chronological=chronological,
            translate_to=translate_to,
            include_seen=opts["include_seen"],
        )
    )
    _running_jobs[chat_id] = {"task": task, "cancel_event": cancel_event}
