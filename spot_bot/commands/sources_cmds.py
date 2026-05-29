"""Multi-source management: /sources, /addsource, /removesource, /channel."""
from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.settings import (
    get_setting, set_setting, get_sources, add_source, remove_source,
)
from spot_bot.translations import t
from spot_bot.commands.common import _get_lang


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
