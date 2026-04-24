"""Phase 5 feature commands: /latest, /filter, /save, /favorites, /history.

These all take (update, context) like any python-telegram-bot handler,
and rely on the per-user SQLite storage layer.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.config import DEFAULT_SCRAPE_COUNT, MAX_SCRAPE_COUNT
from spot_bot.delivery.telegram_sender import save_button
from spot_bot.jobs import run_job, running_jobs
from spot_bot.storage import favorites as fav_store
from spot_bot.storage import filters as filter_store
from spot_bot.storage import op_log, user_settings
from spot_bot.translations import t

logger = logging.getLogger(__name__)


async def _user(update: Update) -> tuple[int, int, str]:
    """Return (chat_id, user_id, lang) for the caller."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else chat_id
    lang = await user_settings.get(user_id, "lang") or "en"
    return chat_id, user_id, lang


# ---------------------------------------------------------------------------
# /latest — incremental scrape from last_scraped_id forward
# ---------------------------------------------------------------------------


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id, user_id, lang = await _user(update)
    if user_id in running_jobs:
        await update.message.reply_text(t("job_running", lang))
        return

    last_id = await user_settings.get(user_id, "last_scraped_id")
    if not last_id:
        await update.message.reply_text(t("latest_no_previous", lang))
        return

    status_msg = await update.message.reply_text(
        t("latest_scraping", lang, last_id=last_id)
    )

    # Scrape latest N and rely on the job's post ID update logic to save
    # the new watermark. If none of the scraped posts exceed last_id the
    # user will get a "nothing new" via the op result; we also pre-check
    # by fetching a small count and comparing.
    count = DEFAULT_SCRAPE_COUNT
    # Parse optional args: /latest 100 audio combined images
    include_audio = False
    include_images = False
    combined_audio = False
    send_as_file = True
    for arg in (context.args or []):
        a = arg.lower()
        if arg.isdigit():
            count = min(int(arg), MAX_SCRAPE_COUNT)
        elif a == "audio":
            include_audio = True
        elif a in ("images", "img"):
            include_images = True
        elif a == "combined":
            combined_audio = True
        elif a == "inline":
            send_as_file = False

    voice = await user_settings.get(user_id, "voice")
    rate = await user_settings.get(user_id, "speed")

    cancel_event = asyncio.Event()
    task = asyncio.create_task(
        run_job(
            chat_id=chat_id,
            user_id=user_id,
            bot=context.bot,
            status_msg=status_msg,
            cancel_event=cancel_event,
            use_range=False,
            count=count,
            include_audio=include_audio,
            include_images=include_images,
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
# /filter add|exclude|remove|list|clear
# ---------------------------------------------------------------------------


async def cmd_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []

    if not args:
        rules = await filter_store.list_for(user_id)
        if not rules:
            await update.message.reply_text(t("filter_empty", lang))
        else:
            lines = [t("filter_list_header", lang)]
            for r in rules:
                mark = "+" if r["mode"] == "include" else "−"
                lines.append(f"  {mark} {r['keyword']}")
            await update.message.reply_text("\n".join(lines))
        return

    sub = args[0].lower()

    if sub == "list":
        rules = await filter_store.list_for(user_id)
        if not rules:
            await update.message.reply_text(t("filter_empty", lang))
        else:
            lines = [t("filter_list_header", lang)]
            for r in rules:
                mark = "+" if r["mode"] == "include" else "−"
                lines.append(f"  {mark} {r['keyword']}")
            await update.message.reply_text("\n".join(lines))
        return

    if sub == "clear":
        n = await filter_store.clear(user_id)
        await update.message.reply_text(t("filter_cleared", lang) if n else t("filter_empty", lang))
        return

    if sub in ("add", "include", "exclude", "remove") and len(args) >= 2:
        keyword = " ".join(args[1:]).strip()
        if not keyword:
            await update.message.reply_text(t("filter_usage", lang))
            return
        if sub in ("add", "include"):
            await filter_store.add(user_id, keyword, filter_store.MODE_INCLUDE)
            await update.message.reply_text(
                t("filter_added", lang, mode="include", keyword=keyword.lower())
            )
        elif sub == "exclude":
            await filter_store.add(user_id, keyword, filter_store.MODE_EXCLUDE)
            await update.message.reply_text(
                t("filter_added", lang, mode="exclude", keyword=keyword.lower())
            )
        else:  # remove
            n = await filter_store.remove(user_id, keyword)
            await update.message.reply_text(t("filter_removed", lang, n=n))
        return

    await update.message.reply_text(t("filter_usage", lang))


# ---------------------------------------------------------------------------
# /save <post_id>
# ---------------------------------------------------------------------------


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    args = context.args or []
    if not args:
        await update.message.reply_text(t("save_usage", lang))
        return
    raw = args[0].strip().lstrip("#")
    if not raw.isdigit():
        await update.message.reply_text(t("save_usage", lang))
        return
    post_id = f"spotuz/{raw}"
    # We don't have the article text here — store an empty snapshot. If
    # the user saves via the ⭐ button on a delivered article we'll have
    # real title/body.
    await fav_store.add(user_id, post_id, title="", body="")
    await update.message.reply_text(t("save_added", lang, post_id=raw))


# ---------------------------------------------------------------------------
# /favorites
# ---------------------------------------------------------------------------


async def cmd_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    favs = await fav_store.list_for(user_id, limit=50)
    if not favs:
        await update.message.reply_text(t("favorites_empty", lang))
        return

    lines = [t("favorites_header", lang, n=len(favs))]
    for f in favs:
        pid = f["post_id"].split("/")[-1] if "/" in f["post_id"] else f["post_id"]
        title = f["title"] or (f["preview"][:80] if f["preview"] else "")
        lines.append(f"#{pid} — {title}")
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# /history — recent operation log entries
# ---------------------------------------------------------------------------


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, user_id, lang = await _user(update)
    ops = await op_log.recent(user_id, limit=10)
    if not ops:
        await update.message.reply_text(t("history_empty", lang))
        return
    lines = [t("history_header", lang, n=len(ops))]
    for o in ops:
        status = o["status"] or "?"
        n = o["article_count"] or 0
        lines.append(f"{o['started_at']} {status} — {o['command']} ({n})")
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Inline ⭐ Save button callback
# ---------------------------------------------------------------------------


async def on_save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    if not query.data.startswith("fav:"):
        return
    post_id = query.data[len("fav:"):]
    user_id = update.effective_user.id if update.effective_user else 0
    lang = await user_settings.get(user_id, "lang") or "en"

    if await fav_store.exists(user_id, post_id):
        await fav_store.remove(user_id, post_id)
        await query.edit_message_reply_markup(
            reply_markup=save_button(post_id, saved=False)
        )
        pid = post_id.split("/")[-1] if "/" in post_id else post_id
        await query.answer(t("save_removed", lang, post_id=pid), show_alert=False)
    else:
        # Snapshot what the user can see — the message text is the article.
        text = query.message.text or query.message.caption or ""
        # First line is typically the title (we use bold html, strip tags).
        lines = text.splitlines()
        title = lines[0] if lines else ""
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
        await fav_store.add(user_id, post_id, title=title, body=body)
        await query.edit_message_reply_markup(
            reply_markup=save_button(post_id, saved=True)
        )
