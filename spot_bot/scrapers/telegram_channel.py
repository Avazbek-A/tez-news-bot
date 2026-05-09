"""Telegram public-channel scraper using httpx + selectolax.

Replaces the previous Playwright-based scraper. The `t.me/s/<channel>`
URL is server-rendered: each request returns ~20 posts as HTML, and
`?before=<post_id>` jumps to a specific point in the timeline. So we
don't need a real browser — just paginated HTTP requests.

Public API preserved (same function names + signatures) so callers in
pipeline.py and bot.py don't change:
- scrape_latest(count, channel_url, ...)
- scrape_range(start_offset, end_offset, channel_url, ...)
- scrape_by_post_ids(start_id, end_id, channel_url, ...)
- scrape_forward_from(anchor_id, count, channel_url, ...)
- find_post_id_by_title(title_query, channel_url, ...)
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Optional

import httpx
from selectolax.parser import HTMLParser

from spot_bot.config import CHANNEL_URL

logger = logging.getLogger(__name__)


# Each t.me/s/<channel>?before=N page returns ~20 posts. We don't scroll
# any more — just walk back via successive ?before= calls.
_POSTS_PER_PAGE_HINT = 20

# Conservative HTTP defaults.
_HTTP_TIMEOUT_SECONDS = 20
_HTTP_RETRIES = 2
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Hard cap on total pages walked in any single scrape, to bound runtime.
_MAX_PAGES_PER_SCRAPE = 200


# ---------------------------------------------------------------------------
# Title-match helpers (used by /scrape from "<title>" mode). Logic unchanged.
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def _normalize_for_match(text):
    """Lowercase, strip HTML tags, collapse whitespace, drop punctuation."""
    if not text:
        return ""
    plain = unescape(_TAG_RE.sub(" ", text))
    plain = _WS_RE.sub(" ", plain).strip().lower()
    plain = _PUNCT_RE.sub(" ", plain)
    plain = _WS_RE.sub(" ", plain).strip()
    return plain


def _post_match_text(post_data):
    """Build a single normalized string from post HTML for substring matching."""
    return _normalize_for_match(post_data.get("text_html", ""))


def _post_first_line(post_data):
    """Return a short (≤120 chars) human-readable preview of the post text."""
    if not post_data:
        return ""
    plain = unescape(_TAG_RE.sub(" ", post_data.get("text_html", "")))
    plain = _WS_RE.sub(" ", plain).strip()
    return plain[:120] + ("…" if len(plain) > 120 else "")


# ---------------------------------------------------------------------------
# Date parsing (unchanged)
# ---------------------------------------------------------------------------

def _parse_date(date_str):
    """Parse Telegram date strings into date objects."""
    today = datetime.now().date()
    try:
        date_str = (date_str or "").lower().strip()
        if "today" in date_str:
            return today
        if "yesterday" in date_str:
            return today - timedelta(days=1)
        date_text = date_str.split(" at ")[0]
        try:
            return datetime.strptime(date_text, "%b %d, %Y").date()
        except ValueError:
            pass
        try:
            dt = datetime.strptime(date_text, "%b %d").date()
            dt = dt.replace(year=today.year)
            if dt > today:
                dt = dt.replace(year=today.year - 1)
            return dt
        except ValueError:
            pass
        if ":" in date_text and len(date_text) < 6:
            return today
    except Exception as e:
        logger.warning("Error parsing date %r: %s", date_str, e)
    return None


def _get_numeric_id(post_id):
    """Extract numeric part from post ID like 'spotuz/35808'."""
    try:
        return int(post_id.split("/")[-1])
    except (ValueError, IndexError):
        return None


def _post_sort_key(post):
    """Sort key for chronological ordering by post ID."""
    pid = post.get("id", "")
    try:
        return int(pid.split("/")[-1])
    except (ValueError, IndexError):
        return 0


# ---------------------------------------------------------------------------
# HTTP fetch + HTML parsing
# ---------------------------------------------------------------------------

async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """GET `url`, return HTML body or None on failure. Retries transient errors."""
    last_exc: Optional[Exception] = None
    for attempt in range(_HTTP_RETRIES + 1):
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            logger.warning(
                "Channel page returned HTTP %d for %s",
                resp.status_code, url,
            )
            return None
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            if attempt < _HTTP_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
    if last_exc is not None:
        logger.warning("Channel fetch gave up on %s: %s", url, last_exc)
    return None


def _extract_posts_from_html(html: str, processed_ids: set):
    """Parse an HTML page and return new (post_data, numeric_id) tuples.

    Mutates `processed_ids` in place — adds every post we touched (including
    ones we couldn't fully parse) so we don't loop on them.
    """
    if not html:
        return []

    tree = HTMLParser(html)
    messages = tree.css(".tgme_widget_message")
    results = []

    for msg in messages:
        try:
            post_id = msg.attributes.get("data-post")
            if not post_id or post_id in processed_ids:
                continue

            # Date
            date_obj = None
            time_el = msg.css_first(".tgme_widget_message_date time")
            if time_el is not None:
                datetime_attr = time_el.attributes.get("datetime")
                if datetime_attr:
                    try:
                        date_obj = datetime.fromisoformat(datetime_attr).date()
                    except ValueError:
                        date_obj = None
                if date_obj is None:
                    date_text = time_el.text(strip=True) or ""
                    date_obj = _parse_date(date_text)

            if date_obj is None:
                # Fall back to any nearby date container
                date_link = msg.css_first(".tgme_widget_message_date")
                if date_link is not None:
                    date_obj = _parse_date(date_link.text(strip=True) or "")

            if date_obj is None:
                processed_ids.add(post_id)
                continue

            # Content
            text_el = msg.css_first(".tgme_widget_message_text.js-message_text")
            text_content = ""
            links: list[str] = []
            if text_el is not None:
                text_content = text_el.html or ""
                for a in text_el.css("a"):
                    href = a.attributes.get("href")
                    if href:
                        links.append(href)

            has_spot_link = any("spot.uz" in l for l in links)

            post_data = {
                "id": post_id,
                "date": date_obj.isoformat(),
                "text_html": text_content,
                "links": links,
                "has_spot_link": has_spot_link,
            }
            processed_ids.add(post_id)
            results.append((post_data, _get_numeric_id(post_id)))
        except Exception as e:
            logger.warning("Error processing message: %s", e)

    return results


def _latest_post_id_from_html(html: str) -> Optional[int]:
    """Return the numeric ID of the newest post on the page, or None."""
    if not html:
        return None
    tree = HTMLParser(html)
    messages = tree.css(".tgme_widget_message")
    if not messages:
        return None
    last = messages[-1]  # newest at the bottom in t.me/s/ pages
    return _get_numeric_id(last.attributes.get("data-post") or "")


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )


# ---------------------------------------------------------------------------
# Public scraper API
# ---------------------------------------------------------------------------

async def scrape_latest(count, channel_url=CHANNEL_URL, cancel_event=None,
                        progress_callback=None, chronological=False):
    """Scrape the latest `count` posts from a Telegram channel."""

    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    captured_posts: list[dict] = []
    processed_ids: set[str] = set()
    pages_walked = 0

    async with _make_client() as client:
        await _report(f"Opening {channel_url}...")
        html = await _fetch_page(client, channel_url)
        if html is None:
            return []

        oldest_id_seen: Optional[int] = None
        while len(captured_posts) < count and pages_walked < _MAX_PAGES_PER_SCRAPE:
            if cancel_event and cancel_event.is_set():
                break

            batch = _extract_posts_from_html(html, processed_ids)
            if not batch:
                break

            for post_data, numeric_id in batch:
                if numeric_id is not None:
                    if oldest_id_seen is None or numeric_id < oldest_id_seen:
                        oldest_id_seen = numeric_id
                captured_posts.append(post_data)
                if len(captured_posts) >= count:
                    break

            pages_walked += 1
            if len(captured_posts) >= count:
                break

            await _report(
                f"Collected {len(captured_posts)}/{count} posts, paging older..."
            )

            if oldest_id_seen is None:
                break
            next_url = f"{channel_url}?before={oldest_id_seen}"
            html = await _fetch_page(client, next_url)
            if html is None:
                break

    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:count]


async def scrape_range(start_offset, end_offset, channel_url=CHANNEL_URL,
                       cancel_event=None, progress_callback=None,
                       chronological=False):
    """Scrape posts within an offset range from the latest."""

    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needed = start_offset - end_offset
    if needed <= 0:
        return []

    captured_posts: list[dict] = []
    processed_ids: set[str] = set()
    pages_walked = 0

    async with _make_client() as client:
        await _report("Finding latest post ID...")
        first_html = await _fetch_page(client, channel_url)
        if first_html is None:
            return []
        latest_id = _latest_post_id_from_html(first_html)
        if latest_id is None:
            return []

        target_id = max(1, latest_id - end_offset)
        jump_url = f"{channel_url}?before={target_id + 1}"
        await _report(
            f"Latest #{latest_id}. Jumping to ~#{target_id} (offset {end_offset})..."
        )
        html = await _fetch_page(client, jump_url)
        if html is None:
            await _report("No posts at this offset.")
            return []

        oldest_id_seen: Optional[int] = None
        while len(captured_posts) < needed and pages_walked < _MAX_PAGES_PER_SCRAPE:
            if cancel_event and cancel_event.is_set():
                break

            batch = _extract_posts_from_html(html, processed_ids)
            if not batch:
                break

            for post_data, numeric_id in batch:
                if numeric_id is not None:
                    if oldest_id_seen is None or numeric_id < oldest_id_seen:
                        oldest_id_seen = numeric_id
                captured_posts.append(post_data)
                if len(captured_posts) >= needed:
                    break

            pages_walked += 1
            if len(captured_posts) >= needed:
                break

            await _report(f"Collected {len(captured_posts)}/{needed} posts...")

            if oldest_id_seen is None:
                break
            html = await _fetch_page(client, f"{channel_url}?before={oldest_id_seen}")
            if html is None:
                break

    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:needed]


async def find_post_id_by_title(title_query, channel_url=CHANNEL_URL,
                                max_search=2000, cancel_event=None,
                                progress_callback=None):
    """Find the most recent post whose normalized text contains `title_query`.

    Returns (numeric_id, post_data) on success or (None, None).
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needle = _normalize_for_match(title_query)
    if not needle:
        return (None, None)

    processed_ids: set[str] = set()
    scanned = 0
    pages_walked = 0

    async with _make_client() as client:
        await _report(f"Searching for article: {title_query[:60]}...")
        html = await _fetch_page(client, channel_url)
        if html is None:
            return (None, None)

        oldest_id_seen: Optional[int] = None
        while scanned < max_search and pages_walked < _MAX_PAGES_PER_SCRAPE:
            if cancel_event and cancel_event.is_set():
                break

            batch = _extract_posts_from_html(html, processed_ids)
            if not batch:
                break

            # Scan newest-first within the batch so the most recent match
            # wins when multiple candidates share the page.
            ordered = sorted(
                batch, key=lambda pair: pair[1] or 0, reverse=True
            )
            for post_data, numeric_id in ordered:
                scanned += 1
                if numeric_id is not None:
                    if oldest_id_seen is None or numeric_id < oldest_id_seen:
                        oldest_id_seen = numeric_id
                haystack = _post_match_text(post_data)
                if needle in haystack:
                    return (numeric_id, post_data)
                if scanned >= max_search:
                    break

            pages_walked += 1
            if scanned >= max_search:
                break

            await _report(f"Searched {scanned}/{max_search} posts, paging older...")
            if oldest_id_seen is None:
                break
            html = await _fetch_page(client, f"{channel_url}?before={oldest_id_seen}")
            if html is None:
                break

    return (None, None)


async def scrape_forward_from(anchor_id, count, channel_url=CHANNEL_URL,
                              cancel_event=None, progress_callback=None,
                              chronological=False):
    """Scrape `count` posts starting at `anchor_id` and moving forward in time."""
    if count <= 0:
        return []
    over_count = max(count + 5, int(count * 1.3))
    start_id = anchor_id + over_count
    end_id = anchor_id

    posts = await scrape_by_post_ids(
        start_id, end_id,
        channel_url=channel_url,
        cancel_event=cancel_event,
        progress_callback=progress_callback,
        chronological=True,
    )
    posts.sort(key=_post_sort_key)
    posts = posts[:count]
    posts.sort(key=_post_sort_key, reverse=not chronological)
    return posts


async def scrape_by_post_ids(start_id, end_id, channel_url=CHANNEL_URL,
                             cancel_event=None, progress_callback=None,
                             chronological=False):
    """Scrape posts by absolute Telegram post IDs (inclusive range)."""

    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needed = start_id - end_id
    if needed <= 0:
        return []

    captured_posts: list[dict] = []
    processed_ids: set[str] = set()
    pages_walked = 0

    async with _make_client() as client:
        jump_url = f"{channel_url}?before={start_id + 1}"
        await _report(f"Jumping to post #{start_id}...")
        html = await _fetch_page(client, jump_url)
        if html is None:
            return []

        oldest_id_seen: Optional[int] = None
        while len(captured_posts) < needed and pages_walked < _MAX_PAGES_PER_SCRAPE:
            if cancel_event and cancel_event.is_set():
                break

            batch = _extract_posts_from_html(html, processed_ids)
            if not batch:
                break

            below_range = True
            for post_data, numeric_id in batch:
                if numeric_id is None:
                    continue
                if oldest_id_seen is None or numeric_id < oldest_id_seen:
                    oldest_id_seen = numeric_id
                if numeric_id > start_id:
                    continue  # too new, skip
                if numeric_id < end_id:
                    continue  # too old, skip but keep walking
                # In range
                captured_posts.append(post_data)
                below_range = False
                if len(captured_posts) >= needed:
                    break

            pages_walked += 1
            if len(captured_posts) >= needed:
                break

            await _report(
                f"Collected {len(captured_posts)}/{needed} posts (#{start_id} to #{end_id})..."
            )

            # Stop if we've already paged below the target range AND nothing
            # in this page was in range — nothing older will help.
            if oldest_id_seen is not None and oldest_id_seen <= end_id and below_range:
                break
            if oldest_id_seen is None:
                break
            html = await _fetch_page(client, f"{channel_url}?before={oldest_id_seen}")
            if html is None:
                break

    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:needed]
