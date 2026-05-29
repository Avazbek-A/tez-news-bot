"""Content-filter command handlers: /skipseen, /mute, /unmute.

Extracted from bot.py as the first slice of its decomposition. These
handlers only touch settings + translations, so they live cleanly here
without importing bot.py.
"""
from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.settings import get_setting, set_setting
from spot_bot.translations import t


def _get_lang():
    return get_setting("language") or "en"


async def cmd_skipseen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/skipseen [on|off] — toggle skipping already-delivered posts on a
    plain `/scrape N`. Use the `all` flag on /scrape to override one run."""
    args = context.args or []
    lang = _get_lang()
    current = bool(get_setting("skip_seen"))

    if not args:
        await update.message.reply_text(
            t("skipseen_status_on" if current else "skipseen_status_off", lang)
        )
        return

    choice = args[0].lower()
    if choice in ("on", "1", "yes", "true"):
        new_value = True
    elif choice in ("off", "0", "no", "false"):
        new_value = False
    else:
        await update.message.reply_text(t("skipseen_usage", lang))
        return

    set_setting("skip_seen", new_value)
    await update.message.reply_text(
        t("skipseen_set_on" if new_value else "skipseen_set_off", lang)
    )


def _format_mutes(lang):
    """Build a human-readable summary of the active mute rules."""
    currency_on = bool(get_setting("mute_currency"))
    keywords = list(get_setting("muted_keywords") or [])
    parts = []
    parts.append(
        t("mute_currency_on", lang) if currency_on
        else t("mute_currency_off", lang)
    )
    if keywords:
        parts.append(t("mute_keywords_list", lang, list=", ".join(keywords)))
    else:
        parts.append(t("mute_keywords_none", lang))
    return "\n".join(parts)


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mute [currency|<keyword ...>] — mute the recurring currency posts
    or add keyword(s). No args shows the current mute rules."""
    args = context.args or []
    lang = _get_lang()

    if not args:
        await update.message.reply_text(_format_mutes(lang))
        return

    if args[0].lower() == "currency":
        set_setting("mute_currency", True)
        await update.message.reply_text(t("mute_currency_set", lang))
        return

    # Treat all args as keywords to add.
    new_kws = [a.strip().lower() for a in args if a.strip()]
    existing = list(get_setting("muted_keywords") or [])
    for kw in new_kws:
        if kw not in existing:
            existing.append(kw)
    set_setting("muted_keywords", existing)
    await update.message.reply_text(
        t("mute_keywords_added", lang, list=", ".join(new_kws))
    )


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unmute [currency|all|<keyword ...>] — undo a mute rule."""
    args = context.args or []
    lang = _get_lang()

    if not args:
        await update.message.reply_text(t("unmute_usage", lang))
        return

    first = args[0].lower()
    if first == "currency":
        set_setting("mute_currency", False)
        await update.message.reply_text(t("unmute_currency_set", lang))
        return
    if first in ("all", "clear", "none"):
        set_setting("muted_keywords", [])
        set_setting("mute_currency", False)
        await update.message.reply_text(t("unmute_all", lang))
        return

    drop = {a.strip().lower() for a in args if a.strip()}
    existing = list(get_setting("muted_keywords") or [])
    remaining = [kw for kw in existing if kw not in drop]
    set_setting("muted_keywords", remaining)
    await update.message.reply_text(
        t("unmute_keywords_removed", lang, list=", ".join(sorted(drop)))
    )
