#!/usr/bin/env python3
"""Entry point for the Spot News Telegram Bot."""

import logging
import time

from telegram.error import Conflict

from spot_bot.bot import create_app
from spot_bot.config import BOT_TOKEN
from spot_bot.observability import init_sentry

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)


# How many times to retry app.run_polling() if Telegram returns a Conflict
# (another instance is still polling). Five seconds between attempts gives
# Railway's rolling-restart enough time to drain the previous container.
_STARTUP_MAX_ATTEMPTS = 6
_STARTUP_RETRY_SECONDS = 5


def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("ERROR: Set your BOT_TOKEN in the .env file.")
        print("  1. Talk to @BotFather on Telegram to create a bot")
        print("  2. Copy the token into .env: BOT_TOKEN=123456:ABC-DEF...")
        return

    init_sentry()

    print("Starting Spot News Bot...")
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
                print(
                    f"Persistent getUpdates Conflict after "
                    f"{_STARTUP_MAX_ATTEMPTS} attempts. Another instance "
                    f"appears to be holding the long-poll. Giving up."
                )
                raise
            print(
                f"Startup Conflict (attempt {attempt}/"
                f"{_STARTUP_MAX_ATTEMPTS}); retrying in "
                f"{_STARTUP_RETRY_SECONDS}s..."
            )
            time.sleep(_STARTUP_RETRY_SECONDS)


if __name__ == "__main__":
    main()
