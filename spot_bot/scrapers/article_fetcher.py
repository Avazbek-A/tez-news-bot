from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from spot_bot.cleaners.html_cleaner import clean_html, clean_telegram_text
from spot_bot.config import (
    MAX_CONCURRENT_FETCHES,
    PLAYWRIGHT_NAV_TIMEOUT_MS,
    PLAYWRIGHT_SELECTOR_TIMEOUT_MS,
)
from spot_bot.scrapers.browser_pool import get_context
from spot_bot.storage import article_cache
from spot_bot.utils.retry import async_retry

logger = logging.getLogger(__name__)

# Local aliases — matches pipeline.Article. Importing from pipeline would
# create a cycle, so we redefine.
Post = dict[str, Any]
Article = dict[str, Any]
ProgressCallback = Callable[[str], Awaitable[None]]


@async_retry(max_attempts=2, initial_backoff=1.5)
async def _navigate_with_retry(page: Any, url: str) -> None:
    """Navigate to URL with a single retry on transient failures.

    Only retries navigation, not selector waits or content extraction —
    those either succeed or are handled by graceful fallbacks.
    """
    await page.goto(url, timeout=PLAYWRIGHT_NAV_TIMEOUT_MS,
                    wait_until="domcontentloaded")


async def fetch_articles(
    posts: list[Post],
    include_images: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> list[Article]:
    """Fetch full article content for posts that link to spot.uz.

    For posts without a spot.uz link, uses the Telegram post text directly.

    Args:
        posts: List of post dicts from the scraper.
        include_images: If True, extract article images (slower).
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        List of article dicts with keys: title, body, date, source, images.
    """
    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
    articles: list[Article] = []
    skipped: list[str] = []

    # Use the shared browser pool — much faster than launching Chromium
    # per fetch_articles() call.
    context = await get_context()

    tasks = [
        _process_post(context, post, semaphore, include_images)
        for post in posts
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    done = 0
    for i, result in enumerate(results):
        done += 1
        post_id = posts[i].get("id", f"unknown-{i}")
        if isinstance(result, BaseException):
            logger.error("Fetch error for %s: %s", post_id, result, exc_info=result)
            skipped.append(post_id)
            continue
        if result:
            # Narrow: gather returned a dict since the else-branch handled
            # exceptions.
            article: Article = result
            article["id"] = posts[i].get("id", "")
            articles.append(article)
        else:
            logger.warning("Fetch returned None for %s", post_id)
            skipped.append(post_id)
        if done % 10 == 0:
            await _report(f"Fetched {done}/{len(posts)} articles...")

    if skipped:
        await _report(f"Fetched {len(articles)} articles ({len(skipped)} failed: {', '.join(skipped)}).")
    else:
        await _report(f"Fetched {len(articles)} articles total.")
    return articles


async def _process_post(
    context: Any,
    post: Post,
    semaphore: asyncio.Semaphore,
    include_images: bool = False,
) -> Article:
    """Process a single post: fetch the full article or use Telegram text."""
    telegram_text = clean_telegram_text(post.get("text_html", ""))
    date = post.get("date", "")

    # Find spot.uz link
    link: str | None = None
    if post.get("has_spot_link"):
        for candidate in post.get("links", []):
            if "spot.uz" in candidate:
                link = candidate
                break

    # No spot.uz link — use Telegram text directly
    if not link:
        return {
            "title": "",
            "body": telegram_text,
            "date": date,
            "source": "telegram",
            "images": [],
        }

    # Cache hit? Short-circuit before even acquiring the semaphore — no
    # page needed.
    cached = await article_cache.lookup(link)
    if cached is not None:
        logger.debug("Cache hit for %s", link)
        return {
            "title": cached["title"],
            "body": cached["body"],
            "date": date,
            "source": cached["source"],
            "images": cached["images"] if include_images else [],
        }

    # Fetch full article from spot.uz
    async with semaphore:
        page = None
        try:
            page = await context.new_page()

            # Block resources for speed; keep images if requested
            if include_images:
                await page.route(
                    "**/*.{svg,css,woff,woff2}",
                    lambda route: route.abort(),
                )
            else:
                await page.route(
                    "**/*.{png,jpg,jpeg,svg,css,woff,woff2}",
                    lambda route: route.abort(),
                )

            try:
                await _navigate_with_retry(page, link)
                try:
                    await page.wait_for_selector(
                        ".contentBox", timeout=PLAYWRIGHT_SELECTOR_TIMEOUT_MS,
                    )
                except Exception:
                    pass  # Proceed anyway — some articles lack this class

                content = await page.content()
            except Exception as nav_e:
                logger.warning("Nav error for %s: %s", link, nav_e)
                return {
                    "title": "",
                    "body": telegram_text,
                    "date": date,
                    "source": "telegram_fallback",
                    "images": [],
                }

            if not content:
                return {
                    "title": "",
                    "body": telegram_text,
                    "date": date,
                    "source": "telegram_fallback",
                    "images": [],
                }

            headline, body, images = clean_html(content, base_url=link)

            if not body:
                return {
                    "title": headline or "",
                    "body": telegram_text,
                    "date": date,
                    "source": "telegram_fallback",
                    "images": images if include_images else [],
                }

            # Populate cache for next time.
            await article_cache.store(
                link, headline or "", body, images, source="spot.uz",
            )
            return {
                "title": headline or "",
                "body": body,
                "date": date,
                "source": "spot.uz",
                "images": images if include_images else [],
            }

        except Exception as e:
            logger.error("Error fetching %s: %s", post.get("id"), e, exc_info=True)
            return {
                "title": "",
                "body": telegram_text,
                "date": date,
                "source": "telegram_error",
                "images": [],
            }
        finally:
            if page:
                await page.close()
