"""Library / history / analytics commands: /stats, /metrics, /find,
/unread, /bookmarks, /bookmark, /unbookmark, /resume, plus the share and
bookmark inline-button callbacks.

Depends on common (for _get_lang) + settings/history_db/translations.
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from spot_bot.settings import (
    get_setting, set_setting,
    get_bookmarks, add_bookmark, remove_bookmark, get_sources,
)
from spot_bot.translations import t
from spot_bot import history_db
from spot_bot.commands.common import _get_lang

logger = logging.getLogger(__name__)


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


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/metrics — operational health (last 7 days), read from the local
    SQLite metrics. No external monitoring system; travels with the DB."""
    lang = _get_lang()
    m = history_db.metrics_snapshot(days=7)
    runs = m["runs"]
    # Error/partial rates as percentages of total runs (guard div-by-zero).
    err_pct = round(100 * m["errors"] / runs) if runs else 0
    partial_pct = round(100 * m["partial"] / runs) if runs else 0
    avg_s = round(m["avg_duration_ms"] / 1000, 1)
    text = t(
        "metrics_body", lang,
        days=m["days"],
        runs=runs,
        today_runs=m["today_runs"],
        today_articles=m["today_articles"],
        articles=m["articles"],
        audio=m["audio"],
        images=m["images"],
        skipped_seen=m["skipped_seen"],
        muted=m["muted"],
        errors=m["errors"],
        err_pct=err_pct,
        partial=m["partial"],
        partial_pct=partial_pct,
        avg_s=avg_s,
    )
    await update.message.reply_text(text)


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


async def cmd_unread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang()
    delivered = get_setting("delivered_post_ids") or []
    if not delivered:
        await update.message.reply_text(t("unread_empty", lang))
        return

    last_seen = max(delivered)

    # Probe the channel's current latest post ID via the httpx scraper.
    # (Previously used Playwright helpers that were removed in Phase 2.)
    from spot_bot.scrapers.telegram_channel import (
        _make_client, _fetch_page, _latest_post_id_from_html,
    )
    channel_url = get_setting("channel_url")
    try:
        async with _make_client() as client:
            html = await _fetch_page(client, channel_url)
        latest_id = _latest_post_id_from_html(html) if html else None
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
