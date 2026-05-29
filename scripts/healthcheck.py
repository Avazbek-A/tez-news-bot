#!/usr/bin/env python3
"""Synthetic check: verify the live scraper still works end-to-end.

Run on a schedule (GitHub Actions cron, Railway cron, or any monitor that
can execute a command). Exits 0 when healthy, 1 when a structural check
fails (markup changed, site unreachable) — so the scheduler/monitor
alerts the operator.

    python -m scripts.healthcheck            # check the default channel
    python -m scripts.healthcheck <url>      # check a specific channel URL

No BOT_TOKEN required.
"""
import asyncio
import os
import sys

# Allow running both as `python -m scripts.healthcheck` and `python scripts/healthcheck.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The canary doesn't need a real bot token, but config import expects the
# env var to exist — set a dummy if absent.
os.environ.setdefault("BOT_TOKEN", "canary:dummy")

from spot_bot.config import CHANNEL_URL  # noqa: E402
from spot_bot.health import run_canary, format_canary  # noqa: E402


async def _main() -> int:
    channel = sys.argv[1] if len(sys.argv) > 1 else CHANNEL_URL
    report = await run_canary(channel)
    print(format_canary(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
