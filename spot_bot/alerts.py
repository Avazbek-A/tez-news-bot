"""Operational alerting — "you knew before the client did".

Two triggers, both evaluated cheaply at the end of every scrape run:

1. Zero-yield breakage: a plain "latest" scrape that returned zero
   articles with NO skip/mute reason and no network truncation. That's
   the signature of the scrapers' CSS selectors going stale (Telegram or
   spot.uz changed their markup) — the failure mode this whole module
   exists to catch.
2. Sustained error rate: when the recent error rate (from the metrics
   table) crosses a threshold.

Delivery is best-effort and layered: always a logger.error (which Sentry
captures via its logging integration when SENTRY_DSN is set), plus an
optional Telegram message to ALERT_CHAT_ID. A cooldown prevents spam.
No external alerting system required; it works the same on Railway or a
Linux laptop.
"""
from __future__ import annotations

import logging
import os
import time

from spot_bot import history_db

logger = logging.getLogger(__name__)

# Don't re-alert more than once per this window (seconds), per alert key.
_ALERT_COOLDOWN_SECONDS = 3600
_last_alert_at: dict[str, float] = {}

# Sustained-error threshold: alert when >= this fraction of recent runs
# errored, over at least this many runs.
_ERROR_RATE_THRESHOLD = 0.5
_ERROR_RATE_MIN_RUNS = 3


def _cooldown_ok(key: str) -> bool:
    """True if we haven't alerted on `key` within the cooldown window."""
    now = time.monotonic()
    last = _last_alert_at.get(key)
    if last is not None and (now - last) < _ALERT_COOLDOWN_SECONDS:
        return False
    _last_alert_at[key] = now
    return True


async def send_alert(bot, text: str) -> None:
    """Emit an operational alert. Best-effort — never raises.

    Always logs at ERROR (→ Sentry when configured). Also sends to
    ALERT_CHAT_ID via Telegram when that env var is set and a bot is
    available.
    """
    logger.error("[ALERT] %s", text)
    chat_id = (os.environ.get("ALERT_CHAT_ID") or "").strip()
    if bot is not None and chat_id:
        try:
            await bot.send_message(chat_id=int(chat_id), text=f"🚨 {text}")
        except Exception as e:
            logger.warning("[alerts] Telegram alert send failed: %s", e)


async def evaluate_scrape_health(bot, *, result, run_ok, latest_mode,
                                 requested_count) -> None:
    """Inspect one finished run and alert on breakage signals.

    Args:
        bot: Telegram bot (for ALERT_CHAT_ID delivery); may be None.
        result: PipelineResult (or None if the run errored early).
        run_ok: False if the run raised.
        latest_mode: True for a plain "latest N" scrape (not an explicit
            range/post-id/title request, where an empty result can be a
            legitimate answer).
        requested_count: how many posts were asked for.
    """
    try:
        # 1. Zero-yield on a latest scrape with no benign explanation.
        if (run_ok and latest_mode and requested_count and result is not None
                and not result.articles
                and not result.skipped_seen_count
                and not result.muted_count
                and not result.partial):
            if _cooldown_ok("zero_yield"):
                await send_alert(
                    bot,
                    f"Zero-yield scrape: asked for {requested_count} latest "
                    f"posts, got 0 with no skip/mute/network reason. Likely "
                    f"the channel/spot.uz markup changed — check the scraper "
                    f"selectors.",
                )

        # 2. Sustained error rate from recent runs.
        snap = history_db.metrics_snapshot(days=1)
        runs = snap.get("runs", 0)
        errors = snap.get("errors", 0)
        if runs >= _ERROR_RATE_MIN_RUNS:
            rate = errors / runs
            if rate >= _ERROR_RATE_THRESHOLD and _cooldown_ok("error_rate"):
                await send_alert(
                    bot,
                    f"High scrape error rate: {errors}/{runs} runs failed in "
                    f"the last 24h ({round(rate * 100)}%). Investigate logs.",
                )
    except Exception as e:
        # Alerting must never break the bot.
        logger.warning("[alerts] evaluate_scrape_health failed: %s", e)
