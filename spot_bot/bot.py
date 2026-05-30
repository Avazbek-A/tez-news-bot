"""Telegram bot wiring.

After the Phase 17 decomposition, bot.py is just the application factory:
it imports the command handlers from the cohesive modules under
spot_bot/commands/ and registers them. All handler logic lives in those
modules; the shared per-chat state + helpers live in commands/common.py.
"""
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from spot_bot.config import BOT_TOKEN, DEFAULT_AUTO_SCRAPE_COUNT
from spot_bot.settings import get_setting
from spot_bot.observability import start_heartbeat_task
from spot_bot import help as help_module

# Command handlers, grouped by concern.
from spot_bot.commands.scrape import (
    cmd_scrape,
    cmd_cancel,
    _handle_scrape_menu_callback,
    _handle_next_batch,
)
from spot_bot.commands.runner import _handle_anchor_confirmation
from spot_bot.commands.settings_cmds import (
    cmd_voice,
    cmd_speed,
    cmd_lang,
    cmd_order,
    cmd_voice_engine,
    cmd_translate,
    cmd_summarize,
    cmd_quality,
    cmd_topics,
    cmd_dedup,
    cmd_ads,
)
from spot_bot.commands.filter_cmds import cmd_skipseen, cmd_mute, cmd_unmute
from spot_bot.commands.dates import (
    cmd_today,
    cmd_yesterday,
    cmd_thisweek,
    cmd_since,
)
from spot_bot.commands.library_cmds import (
    cmd_stats,
    cmd_metrics,
    cmd_find,
    cmd_unread,
    cmd_bookmarks,
    cmd_bookmark,
    cmd_unbookmark,
    cmd_resume,
    _handle_resume_mark,
    _handle_share_callback,
    _handle_bookmark_callback,
)
from spot_bot.commands.sources_cmds import (
    cmd_sources,
    cmd_addsource,
    cmd_removesource,
    cmd_channel,
)
from spot_bot.commands.status_cmd import cmd_status, cmd_chatid
from spot_bot.commands.auto import cmd_auto, _schedule_auto_scrape

logger = logging.getLogger(__name__)


async def _post_init(app: Application):
    """Restore scheduled jobs and start observability hooks on startup."""
    config = get_setting("auto_scrape")
    if config and config.get("enabled"):
        _schedule_auto_scrape(app, config)
        logger.info(
            "Auto-scrape restored: %s, %d articles",
            (f"every {config['interval_days']} day(s)"
             if config.get("interval_days") else config.get("mode", "cron")),
            config.get("count", DEFAULT_AUTO_SCRAPE_COUNT),
        )

    # Outbound heartbeat (no-op when HEARTBEAT_URL is unset).
    start_heartbeat_task()

    # Phase 15: install bot identity (description + commands menu) so
    # /-autocomplete and the bot's profile screen show curated copy in
    # the user's UI language.
    try:
        await help_module.install_bot_identity(app)
    except Exception as e:
        logger.warning("[identity] install_bot_identity failed: %s", e)


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

    app.add_handler(CommandHandler("start", help_module.cmd_start))
    app.add_handler(CommandHandler("help", help_module.cmd_help))
    app.add_handler(CommandHandler("help_scrape", help_module.cmd_help_scrape))
    app.add_handler(CommandHandler("help_auto", help_module.cmd_help_auto))
    app.add_handler(CommandHandler("help_audio", help_module.cmd_help_audio))
    app.add_handler(CommandHandler("help_filter", help_module.cmd_help_filter))
    app.add_handler(CommandHandler("help_library", help_module.cmd_help_library))
    app.add_handler(CommandHandler("help_languages", help_module.cmd_help_languages))
    app.add_handler(CommandHandler("help_system", help_module.cmd_help_system))
    app.add_handler(CommandHandler("about", help_module.cmd_about))
    app.add_handler(CallbackQueryHandler(
        help_module.handle_help_callback,
        pattern=r"^help_",
    ))
    app.add_handler(CommandHandler("scrape", cmd_scrape))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("speed", cmd_speed))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("channel", cmd_channel))
    app.add_handler(CommandHandler("order", cmd_order))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("auto", cmd_auto))
    app.add_handler(CommandHandler("ads", cmd_ads))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("voice_engine", cmd_voice_engine))
    app.add_handler(CommandHandler("quality", cmd_quality))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("dedup", cmd_dedup))
    app.add_handler(CommandHandler("skipseen", cmd_skipseen))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
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
    app.add_handler(CommandHandler("metrics", cmd_metrics))
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
        _handle_next_batch,
        pattern=r"^nb_",
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
