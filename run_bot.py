#!/usr/bin/env python3
"""Entry point for the Spot News Telegram Bot."""

import logging
import time

from telegram.error import Conflict

from spot_bot.logging_setup import configure_logging

# Configure logging first, before any spot_bot module wires its own loggers.
configure_logging()

from spot_bot.bot import create_app  # noqa: E402
from spot_bot.config import BOT_TOKEN  # noqa: E402
from spot_bot.observability import init_sentry  # noqa: E402

logger = logging.getLogger(__name__)


# How many times to retry app.run_polling() if Telegram returns a Conflict
# (another instance is still polling). Five seconds between attempts gives
# Railway's rolling-restart enough time to drain the previous container.
_STARTUP_MAX_ATTEMPTS = 6
_STARTUP_RETRY_SECONDS = 5


def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("BOT_TOKEN not set. Configure it via environment "
                     "or .env (BOT_TOKEN=123456:ABC-DEF...).")
        return

    init_sentry()

    logger.info("Starting Spot News Bot...")
    app = create_app()
    # Heartbeat scheduling is inside bot._post_init so it runs once the
    # bot's event loop is up and stays up.

    # If another bot instance is still finishing teardown when we start
    # (e.g. during a Railway rolling-restart), Telegram may reject our first
    # getUpdates with Conflict. Retry briefly so the new container survives
    # its own birth instead of crashing and triggering a rollback.
    for attempt in range(1, _STARTUP_MAX_ATTEMPTS + 1):
        try:
            app.run_polling()
            return
        except Conflict:
            if attempt >= _STARTUP_MAX_ATTEMPTS:
                logger.error(
                    "Persistent getUpdates Conflict after %d attempts. "
                    "Another instance appears to be holding the long-poll. "
                    "Giving up.",
                    _STARTUP_MAX_ATTEMPTS,
                )
                raise
            logger.warning(
                "Startup Conflict (attempt %d/%d); retrying in %ds...",
                attempt, _STARTUP_MAX_ATTEMPTS, _STARTUP_RETRY_SECONDS,
            )
            time.sleep(_STARTUP_RETRY_SECONDS)


if __name__ == "__main__":
    main()
