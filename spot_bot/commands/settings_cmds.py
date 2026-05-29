"""Preference/setting command handlers (stateless toggles + selectors):
/voice, /speed, /lang, /order, /voice_engine, /translate, /summarize,
/quality, /topics, /dedup, /ads.

These touch only settings + translations, so they depend on `common`
alone.
"""
import re

from telegram import Update
from telegram.ext import ContextTypes

from spot_bot.config import (
    AVAILABLE_VOICES,
    AVAILABLE_SPEEDS,
    AVAILABLE_LANGUAGES,
)
from spot_bot.settings import get_setting, set_setting
from spot_bot.translations import t
from spot_bot.commands.common import (
    _get_lang,
    _get_voice,
    _get_speed,
    _build_voice_list,
    _TRANSLATE_LANGS,
)


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
