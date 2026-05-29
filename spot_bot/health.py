"""Live selector canary.

Fetches the real channel + a real spot.uz article and verifies the
scraper/cleaner still extract what we expect. This catches the failure
mode unit tests can't: Telegram or spot.uz silently changing their markup
so our CSS selectors stop matching.

Run it as a synthetic check on a schedule (see .github/workflows/canary.yml
or any cron) — it exits non-zero and reports which check broke, so the
operator is alerted before users notice empty scrapes.
"""
from __future__ import annotations

import logging

from spot_bot.config import CHANNEL_URL
from spot_bot.scrapers.telegram_channel import (
    _make_client,
    _fetch_page,
    _extract_posts_from_html,
)
from spot_bot.scrapers.article_fetcher import _get_article_html
from spot_bot.cleaners.html_cleaner import clean_html

logger = logging.getLogger(__name__)


async def run_canary(channel_url: str = CHANNEL_URL) -> dict:
    """Run the live structural checks. Returns a dict:

        {"ok": bool, "checks": {name: {"ok": bool, "detail": str}, ...}}

    Each check is independent so a partial break is pinpointed.
    """
    checks: dict[str, dict] = {}

    def _record(name, ok, detail=""):
        checks[name] = {"ok": bool(ok), "detail": detail}

    # --- Channel page reachable + parseable into posts ---
    posts = []
    spot_link = None
    try:
        async with _make_client() as client:
            html = await _fetch_page(client, channel_url)
        if not html:
            _record("channel_reachable", False, "no HTML returned")
        else:
            _record("channel_reachable", True, f"{len(html)} bytes")
            batch = _extract_posts_from_html(html, set())
            posts = [p for p, _ in batch]
            _record(
                "channel_posts_parsed", bool(posts),
                f"{len(posts)} posts extracted",
            )
            # Find a spot.uz article link to exercise the article path.
            for p in posts:
                for link in p.get("links", []):
                    if "spot.uz" in link and "/20" in link:
                        spot_link = link
                        break
                if spot_link:
                    break
            _record(
                "channel_spot_link_found", bool(spot_link),
                spot_link or "no spot.uz article link on the page",
            )
    except Exception as e:
        _record("channel_reachable", False, repr(e))

    # --- Article fetch + clean extracts a real body ---
    if spot_link:
        try:
            async with _make_client() as client:
                article_html = await _get_article_html(client, spot_link)
            if not article_html:
                _record("article_fetch", False, f"no HTML from {spot_link}")
            else:
                _record("article_fetch", True, f"{len(article_html)} bytes")
                headline, body, images = clean_html(
                    article_html, base_url=spot_link
                )
                _record(
                    "article_headline", bool(headline),
                    (headline or "")[:60],
                )
                # A real article should clean down to a non-trivial body.
                _record(
                    "article_body", bool(body and len(body) > 200),
                    f"{len(body or '')} chars",
                )
                # Images are optional per-article, so this is informational
                # (always ok) — but we report the count.
                _record(
                    "article_images", True,
                    f"{len(images)} image(s)",
                )
        except Exception as e:
            _record("article_fetch", False, repr(e))

    ok = all(c["ok"] for c in checks.values()) and bool(checks)
    return {"ok": ok, "checks": checks}


def format_canary(report: dict) -> str:
    """Human-readable one-block summary of a canary report."""
    lines = ["OK" if report["ok"] else "FAIL"]
    for name, c in report["checks"].items():
        mark = "✓" if c["ok"] else "✗"
        lines.append(f"  {mark} {name}: {c['detail']}")
    return "\n".join(lines)
