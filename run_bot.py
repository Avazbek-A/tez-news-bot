#!/usr/bin/env python3
"""Entry point for the Spot News Telegram Bot."""

import logging

from spot_bot.bot import create_app
from spot_bot.config import BOT_TOKEN
from spot_bot.logging_config import setup_logging


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        # BOT_TOKEN missing is a user setup problem, not a code error — print
        # to stdout so it appears in any terminal invocation, even if logging
        # is routed elsewhere.
        print("ERROR: Set your BOT_TOKEN in the .env file.")
        print("  1. Talk to @BotFather on Telegram to create a bot")
        print("  2. Copy the token into .env: BOT_TOKEN=123456:ABC-DEF...")
        return

    logger.info("Starting Spot News Bot...")
    app = create_app()
    app.run_polling()


if __name__ == "__main__":
    main()
