"""/status — current settings + running-job + auto-scrape summary."""
from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.config import (
    DEFAULT_AUTO_SCRAPE_COUNT,
    DEFAULT_SCRAPE_COUNT,
    MAX_SCRAPE_COUNT,
    MAX_OFFSET,
)
from spot_bot.settings import get_setting
from spot_bot.translations import t
from spot_bot.commands.common import (
    _running_jobs, _get_lang, _get_voice, _get_speed,
)


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


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/chatid — report this chat's numeric ID. Use it to set the
    ALERT_CHAT_ID env var so operational alerts are delivered here."""
    chat_id = update.effective_chat.id
    lang = _get_lang()
    await update.message.reply_text(t("chatid_body", lang, chat_id=chat_id))
