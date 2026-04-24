from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from typing import Any

from spot_bot.config import (
    CHANNEL_URL,
    PLAYWRIGHT_CHANNEL_TIMEOUT_MS,
    SCROLL_BACK_PX,
    SCROLL_WAIT_MS,
    STALL_THRESHOLD,
)
from spot_bot.scrapers.browser_pool import page as browser_page

logger = logging.getLogger(__name__)

# Public types
Post = dict[str, Any]
ProgressCallback = Callable[[str], Awaitable[None]]
PostPredicate = Callable[[int], bool]  # numeric_id -> keep?


def _parse_date(date_str: str | None) -> date | None:
    """Parse Telegram date strings into date objects.

    Handles: ISO datetime attrs, "Jan 17, 2026", "Jan 17", "14:30",
    "today at ...", "yesterday at ...".
    """
    today = datetime.now().date()
    if not date_str:
        return None
    try:
        date_str = date_str.lower().strip()

        if "today" in date_str:
            return today
        if "yesterday" in date_str:
            return today - timedelta(days=1)

        date_text = date_str.split(" at ")[0]

        # "Jan 17, 2026"
        try:
            return datetime.strptime(date_text, "%b %d, %Y").date()
        except ValueError:
            pass

        # "Jan 17" (no year)
        try:
            dt = datetime.strptime(date_text, "%b %d").date()
            dt = dt.replace(year=today.year)
            if dt > today:
                dt = dt.replace(year=today.year - 1)
            return dt
        except ValueError:
            pass

        # Just time "14:30" -> today
        if ":" in date_text and len(date_text) < 6:
            return today

    except Exception as e:
        logger.warning("Error parsing date '%s': %s", date_str, e)
    return None


def _get_numeric_id(post_id: str | None) -> int | None:
    """Extract numeric part from post ID like 'spotuz/35808'."""
    if not post_id:
        return None
    try:
        return int(post_id.split("/")[-1])
    except (ValueError, IndexError):
        return None


def _post_sort_key(post: Post) -> int:
    """Sort key for chronological ordering by post ID."""
    pid = post.get("id", "")
    try:
        return int(pid.split("/")[-1])
    except (ValueError, IndexError):
        return 0


async def _extract_posts_from_page(
    page: Any, processed_ids: set[str],
) -> list[tuple[Post, int | None]]:
    """Extract all new posts from the currently loaded page.

    Returns list of (post_data_dict, numeric_id) tuples for posts not in
    processed_ids. Updates processed_ids in place.
    """
    messages = await page.locator(".tgme_widget_message").all()
    if not messages:
        return []

    results: list[tuple[Post, int | None]] = []

    for msg in messages:
        try:
            post_id = await msg.get_attribute("data-post")
            if not post_id or post_id in processed_ids:
                continue

            # Date
            date_obj = None
            date_elem = msg.locator(".tgme_widget_message_date time")
            if await date_elem.count() > 0:
                datetime_attr = await date_elem.get_attribute("datetime")
                if datetime_attr:
                    date_obj = datetime.fromisoformat(datetime_attr).date()
                else:
                    date_text = await msg.locator(
                        ".tgme_widget_message_date"
                    ).text_content()
                    date_obj = _parse_date(date_text)
            else:
                date_link = msg.locator(".tgme_widget_message_date")
                if await date_link.count() > 0:
                    date_text = await date_link.text_content()
                    date_obj = _parse_date(date_text)

            if not date_obj:
                logger.warning("Could not parse date for post %s, using today as fallback", post_id)
                date_obj = datetime.now().date()

            # Content
            text_content = ""
            text_locator = msg.locator(
                ".tgme_widget_message_text.js-message_text"
            )
            if await text_locator.count() > 0:
                text_content = await text_locator.inner_html()

            # Links
            links: list[str] = []
            if await text_locator.count() > 0:
                a_tags = text_locator.locator("a")
                a_count = await a_tags.count()
                for i in range(a_count):
                    href = await a_tags.nth(i).get_attribute("href")
                    if href:
                        links.append(href)

            has_spot_link = any("spot.uz" in link for link in links)

            post_data = {
                "id": post_id,
                "date": date_obj.isoformat(),
                "text_html": text_content,
                "links": links,
                "has_spot_link": has_spot_link,
            }

            processed_ids.add(post_id)
            numeric_id = _get_numeric_id(post_id)
            results.append((post_data, numeric_id))

        except Exception as e:
            logger.error("Error processing message: %s", e, exc_info=True)

    return results


async def _get_latest_post_id(page: Any) -> int | None:
    """Get the numeric ID of the newest post on the page."""
    messages = await page.locator(".tgme_widget_message").all()
    if not messages:
        return None

    # Last message in DOM is the newest
    last_msg = messages[-1]
    post_id = await last_msg.get_attribute("data-post")
    return _get_numeric_id(post_id)


# ---------------------------------------------------------------------------
# Shared scroll-and-collect loop
# ---------------------------------------------------------------------------


async def _collect_posts(
    page: Any,
    needed: int,
    should_include: PostPredicate | None,
    progress_prefix: str,
    cancel_event: asyncio.Event | None,
    progress_callback: ProgressCallback | None,
) -> list[Post]:
    """Scroll-up pagination loop used by all three scrape entry points.

    Args:
        page: Playwright page already pointed at the Telegram channel/position.
        needed: Target number of posts to collect.
        should_include: Optional predicate on numeric post ID. If provided,
            only posts for which this returns True are collected (and only
            they count toward the stall check). If None, all new posts
            count.
        progress_prefix: Prepended to "N/M posts..." progress messages.
        cancel_event: asyncio.Event or None.
        progress_callback: async callable(str) or None.

    Returns:
        List of post dicts, oldest-first by post ID, truncated to `needed`.
    """
    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    captured_posts: list[Post] = []
    processed_ids: set[str] = set()
    stall_count = 0

    while len(captured_posts) < needed:
        if cancel_event and cancel_event.is_set():
            break

        batch = await _extract_posts_from_page(page, processed_ids)
        added_this_round = 0

        for post_data, numeric_id in batch:
            if should_include is not None:
                if numeric_id is None or not should_include(numeric_id):
                    continue
            captured_posts.append(post_data)
            added_this_round += 1
            if len(captured_posts) >= needed:
                break

        if len(captured_posts) >= needed:
            break

        await _report(
            f"{progress_prefix}{len(captured_posts)}/{needed} posts..."
        )

        # Scroll up to load older messages
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(SCROLL_WAIT_MS)

        if added_this_round == 0:
            stall_count += 1
            if stall_count >= STALL_THRESHOLD:
                await _report(
                    f"Got {len(captured_posts)}/{needed} posts."
                )
                break
            await page.evaluate(f"window.scrollTo(0, -{SCROLL_BACK_PX})")
            await page.wait_for_timeout(SCROLL_WAIT_MS)
        else:
            stall_count = 0

    captured_posts.sort(key=_post_sort_key)
    return captured_posts[:needed]


async def _wait_for_messages(
    page: Any,
    progress_callback: ProgressCallback | None,
    not_found_msg: str,
) -> bool:
    """Wait for `.tgme_widget_message` to appear; return False on timeout."""
    try:
        await page.wait_for_selector(
            ".tgme_widget_message", state="visible",
            timeout=PLAYWRIGHT_CHANNEL_TIMEOUT_MS,
        )
        return True
    except Exception:
        if progress_callback:
            await progress_callback(not_found_msg)
        return False


# ---------------------------------------------------------------------------
# Public scrape entry points
# ---------------------------------------------------------------------------


async def scrape_latest(
    count: int,
    channel_url: str = CHANNEL_URL,
    cancel_event: asyncio.Event | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Post]:
    """Scrape the latest `count` posts from a Telegram channel."""
    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    async with browser_page() as page:
        await _report(f"Opening {channel_url}...")
        await page.goto(channel_url)
        if not await _wait_for_messages(page, progress_callback, "No posts found."):
            return []

        return await _collect_posts(
            page, count,
            should_include=None,
            progress_prefix="Collected ",
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )


async def scrape_range(
    start_offset: int,
    end_offset: int,
    channel_url: str = CHANNEL_URL,
    cancel_event: asyncio.Event | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Post]:
    """Scrape posts within an offset range from the latest.

    Example: scrape_range(2000, 1950) grabs the 1950th-to-2000th newest
    posts (50 posts total). Uses Telegram's ?before= to jump.
    """
    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    needed = start_offset - end_offset

    async with browser_page() as page:
        await _report("Finding latest post ID...")
        await page.goto(channel_url)
        await page.wait_for_selector(".tgme_widget_message", state="visible")

        latest_id = await _get_latest_post_id(page)
        if not latest_id:
            return []

        target_id = max(1, latest_id - end_offset)
        jump_url = f"{channel_url}?before={target_id + 1}"
        await _report(
            f"Latest: #{latest_id}. Jumping to ~#{target_id} "
            f"(offset {end_offset} from latest)..."
        )
        await page.goto(jump_url)

        if not await _wait_for_messages(
            page, progress_callback, "No posts found at this offset."
        ):
            return []

        return await _collect_posts(
            page, needed,
            should_include=None,
            progress_prefix="Collected ",
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )


async def scrape_by_post_ids(
    start_id: int,
    end_id: int,
    channel_url: str = CHANNEL_URL,
    cancel_event: asyncio.Event | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Post]:
    """Scrape posts by absolute Telegram post IDs (inclusive on both ends)."""
    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    needed = start_id - end_id + 1  # inclusive range

    async with browser_page() as page:
        jump_url = f"{channel_url}?before={start_id + 1}"
        await _report(f"Jumping to post #{start_id}...")
        await page.goto(jump_url)

        if not await _wait_for_messages(
            page, progress_callback, "No posts found at this ID.",
        ):
            return []

        return await _collect_posts(
            page, needed,
            should_include=lambda nid: end_id <= nid <= start_id,
            progress_prefix=f"Collected #{start_id}-#{end_id}: ",
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
