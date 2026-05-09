"""Lightweight observability hooks: Sentry error tracking + outbound heartbeat.

Both are no-ops unless their respective env vars (SENTRY_DSN, HEARTBEAT_URL)
are set. That keeps local development and first-deploy flows simple — set
them when you want them, ignore them otherwise.
"""

import asyncio
import os

# Logging fallback when Sentry isn't configured.
import logging

logger = logging.getLogger(__name__)


# How often to ping the heartbeat URL (seconds).
HEARTBEAT_INTERVAL_SECONDS = 60

# How long to wait on a single ping before giving up.
HEARTBEAT_TIMEOUT_SECONDS = 10


def init_sentry():
    """Initialize Sentry if SENTRY_DSN is set. Otherwise no-op.

    Picks sensible defaults: lower-volume traces (10%), capture warnings,
    attach Python and asyncio integrations.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set; Sentry disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry_sdk not installed; SENTRY_DSN ignored.")
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        attach_stacktrace=True,
        release=os.environ.get("RAILWAY_DEPLOYMENT_ID"),
        environment=os.environ.get("RAILWAY_ENVIRONMENT_NAME", "production"),
    )
    logger.info("Sentry initialized.")
    return True


async def _heartbeat_loop(url: str):
    """Background task: ping `url` every HEARTBEAT_INTERVAL_SECONDS forever.

    Failures are logged and swallowed — the bot must keep running even if
    the heartbeat service is down.
    """
    try:
        import aiohttp
    except ImportError:
        logger.warning("aiohttp not installed; heartbeat disabled.")
        return

    timeout = aiohttp.ClientTimeout(total=HEARTBEAT_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                async with session.get(url) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            "Heartbeat got HTTP %d from %s",
                            resp.status, url,
                        )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Heartbeat ping failed: %s", e)

            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise


def start_heartbeat_task():
    """Schedule the heartbeat loop on the running asyncio loop.

    Returns the asyncio.Task or None if HEARTBEAT_URL is unset / invalid.
    Safe to call from sync code as long as an event loop is running.
    """
    url = os.environ.get("HEARTBEAT_URL", "").strip()
    if not url:
        logger.info("HEARTBEAT_URL not set; heartbeat disabled.")
        return None

    if not (url.startswith("http://") or url.startswith("https://")):
        logger.warning("HEARTBEAT_URL must be http(s); got %r. Disabled.", url)
        return None

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.warning("No running event loop; heartbeat not started.")
        return None

    task = loop.create_task(_heartbeat_loop(url))
    logger.info(
        "Heartbeat scheduled: pinging %s every %ds",
        url, HEARTBEAT_INTERVAL_SECONDS,
    )
    return task
