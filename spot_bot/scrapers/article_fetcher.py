"""Fetch full spot.uz article content using httpx (no browser).

For each post that has a spot.uz link, GET the article HTML and pass
through the existing html_cleaner. For posts without a link, fall back
to the Telegram post text.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from spot_bot.config import MAX_CONCURRENT_FETCHES, USER_AGENT
from spot_bot.cleaners.html_cleaner import clean_html, clean_telegram_text

logger = logging.getLogger(__name__)


# Minimum interval between progress reports (seconds), matched to TTS pacing.
_PROGRESS_DEBOUNCE = 2.0

# HTTP timeouts. spot.uz can be slow under load; give it generous time.
_FETCH_TIMEOUT_SECONDS = 25


async def fetch_articles(posts, include_images=False, progress_callback=None,
                         stage_prefix=""):
    """Fetch full article content for posts that link to spot.uz.

    For posts without a spot.uz link, uses the Telegram post text directly.
    """

    async def _report(msg):
        if progress_callback:
            await progress_callback(f"{stage_prefix}{msg}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
    total = len(posts)
    completed = 0
    last_report_time = 0.0
    progress_lock = asyncio.Lock()

    async def _progress_one():
        nonlocal completed, last_report_time
        async with progress_lock:
            completed += 1
            now = time.monotonic()
            if now - last_report_time >= _PROGRESS_DEBOUNCE:
                last_report_time = now
                await _report(f"Fetching articles ({completed}/{total})...")

    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        tasks = [
            _process_post(
                client, post, semaphore, include_images,
                progress_one=_progress_one,
            )
            for post in posts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    articles = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Fetch error: %s", result)
            continue
        if result:
            articles.append(result)

    await _report(f"Fetched {len(articles)}/{total} articles.")
    return articles


async def _process_post(client: httpx.AsyncClient, post, semaphore,
                        include_images=False, progress_one=None):
    """Process a single post: fetch the full article or use Telegram text."""

    async def _tick():
        if progress_one is not None:
            try:
                await progress_one()
            except Exception:
                pass

    telegram_text = clean_telegram_text(post.get("text_html", ""))
    date = post.get("date", "")

    # Find spot.uz link
    link = None
    if post.get("has_spot_link"):
        for l in post.get("links", []):
            if "spot.uz" in l:
                link = l
                break

    if not link:
        await _tick()
        return {
            "title": "",
            "body": telegram_text,
            "date": date,
            "source": "telegram",
            "images": [],
        }

    async with semaphore:
        try:
            try:
                resp = await client.get(link)
            except (httpx.TimeoutException, httpx.NetworkError) as nav_e:
                logger.warning("Nav error for %s: %s", link, nav_e)
                return _telegram_fallback(telegram_text, date, [])

            if resp.status_code != 200:
                logger.warning("HTTP %d for %s", resp.status_code, link)
                return _telegram_fallback(telegram_text, date, [])

            content = resp.text
            if not content:
                return _telegram_fallback(telegram_text, date, [])

            headline, body, images = clean_html(content, base_url=link)

            if not body:
                return _telegram_fallback(
                    telegram_text, date,
                    images if include_images else [],
                    title=headline or "",
                )

            return {
                "title": headline or "",
                "body": body,
                "date": date,
                "source": "spot.uz",
                "images": images if include_images else [],
            }

        except Exception as e:
            logger.warning("Error fetching %s: %s", post.get("id"), e)
            return _telegram_fallback(telegram_text, date, [])
        finally:
            await _tick()


def _telegram_fallback(telegram_text, date, images, title=""):
    return {
        "title": title,
        "body": telegram_text,
        "date": date,
        "source": "telegram_fallback",
        "images": images,
    }
