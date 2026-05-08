import asyncio
import re
from datetime import datetime, timedelta
from html import unescape
from playwright.async_api import async_playwright
from spot_bot.config import CHANNEL_URL


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
    """Build a single normalized string from post HTML for substring matching.

    The Telegram channel post text usually starts with the article headline
    or a short summary, so matching against the full post body covers both
    title and lead paragraphs.
    """
    return _normalize_for_match(post_data.get("text_html", ""))


def _post_first_line(post_data):
    """Return a short (≤120 chars) human-readable preview of the post text."""
    if not post_data:
        return ""
    plain = unescape(_TAG_RE.sub(" ", post_data.get("text_html", "")))
    plain = _WS_RE.sub(" ", plain).strip()
    return plain[:120] + ("…" if len(plain) > 120 else "")


def _parse_date(date_str):
    """Parse Telegram date strings into date objects.

    Handles: ISO datetime attrs, "Jan 17, 2026", "Jan 17", "14:30",
    "today at ...", "yesterday at ...".
    """
    today = datetime.now().date()
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
        print(f"Error parsing date '{date_str}': {e}")
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


async def _extract_posts_from_page(page, processed_ids):
    """Extract all new posts from the currently loaded page.

    Returns list of (post_data_dict, numeric_id) tuples for posts not in
    processed_ids. Updates processed_ids in place.
    """
    messages = await page.locator(".tgme_widget_message").all()
    if not messages:
        return []

    results = []

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
                continue

            # Content
            text_content = ""
            text_locator = msg.locator(
                ".tgme_widget_message_text.js-message_text"
            )
            if await text_locator.count() > 0:
                text_content = await text_locator.inner_html()

            # Links
            links = []
            if await text_locator.count() > 0:
                a_tags = text_locator.locator("a")
                a_count = await a_tags.count()
                for i in range(a_count):
                    href = await a_tags.nth(i).get_attribute("href")
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
            numeric_id = _get_numeric_id(post_id)
            results.append((post_data, numeric_id))

        except Exception as e:
            print(f"Error processing message: {e}")

    return results


async def _get_latest_post_id(page):
    """Get the numeric ID of the newest post on the page."""
    messages = await page.locator(".tgme_widget_message").all()
    if not messages:
        return None

    # Last message in DOM is the newest
    last_msg = messages[-1]
    post_id = await last_msg.get_attribute("data-post")
    return _get_numeric_id(post_id)


async def scrape_latest(count, channel_url=CHANNEL_URL, cancel_event=None,
                        progress_callback=None, chronological=False):
    """Scrape the latest `count` posts from a Telegram channel.

    Args:
        count: Number of posts to collect.
        channel_url: Public Telegram channel URL (t.me/s/...).
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        List of dicts with keys: id, date, text_html, links, has_spot_link.
        Ordered newest-first.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    captured_posts = []
    processed_ids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            await _report(f"Opening {channel_url}...")
            await page.goto(channel_url)
            await page.wait_for_selector(".tgme_widget_message", state="visible")

            stall_count = 0

            while len(captured_posts) < count:
                if cancel_event and cancel_event.is_set():
                    break

                batch = await _extract_posts_from_page(page, processed_ids)

                for post_data, _ in batch:
                    captured_posts.append(post_data)
                    if len(captured_posts) >= count:
                        break

                if len(captured_posts) >= count:
                    break

                await _report(
                    f"Collected {len(captured_posts)}/{count} posts, scrolling..."
                )

                # Scroll up to load older messages
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)

                if not batch:
                    stall_count += 1
                    if stall_count >= 3:
                        await _report(
                            f"No new posts found after scrolling. "
                            f"Got {len(captured_posts)}/{count}."
                        )
                        break
                    await page.evaluate("window.scrollTo(0, -500)")
                    await page.wait_for_timeout(2000)
                else:
                    stall_count = 0
        finally:
            await browser.close()

    # Sort by post ID. Default: newest first (descending).
    # chronological=True flips to oldest first for reading order.
    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:count]


async def scrape_range(start_offset, end_offset, channel_url=CHANNEL_URL,
                       cancel_event=None, progress_callback=None,
                       chronological=False):
    """Scrape posts within an offset range from the latest.

    For example, scrape_range(2000, 1950) gets the 1950th-to-2000th
    newest posts (50 posts total).

    Uses Telegram's ?before= URL to jump directly to the right area,
    then collects the needed number of posts.

    Args:
        start_offset: How far back to start (e.g., 2000 = skip 1999 newest).
        end_offset: How far back to stop (e.g., 1950). Must be < start_offset.
        channel_url: Public Telegram channel URL.
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        List of post dicts, ordered newest-first within the range.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needed = start_offset - end_offset
    captured_posts = []
    processed_ids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            # 1. Load channel to find the latest post ID
            await _report("Finding latest post ID...")
            await page.goto(channel_url)
            await page.wait_for_selector(".tgme_widget_message", state="visible")

            latest_id = await _get_latest_post_id(page)
            if not latest_id:
                return []

            # 2. Jump to the right area using ?before=
            target_id = latest_id - end_offset
            if target_id < 1:
                target_id = 1

            jump_url = f"{channel_url}?before={target_id + 1}"
            await _report(
                f"Latest: #{latest_id}. Jumping to ~#{target_id} "
                f"(offset {end_offset} from latest)..."
            )
            await page.goto(jump_url)

            try:
                await page.wait_for_selector(
                    ".tgme_widget_message", state="visible", timeout=10000
                )
            except Exception:
                await _report("No posts found at this offset.")
                return []

            # 3. Collect posts — no ID filtering, just grab what's here
            stall_count = 0

            while len(captured_posts) < needed:
                if cancel_event and cancel_event.is_set():
                    break

                batch = await _extract_posts_from_page(page, processed_ids)

                for post_data, _ in batch:
                    captured_posts.append(post_data)
                    if len(captured_posts) >= needed:
                        break

                if len(captured_posts) >= needed:
                    break

                await _report(
                    f"Collected {len(captured_posts)}/{needed} posts..."
                )

                # Scroll up to load older messages
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)

                if not batch:
                    stall_count += 1
                    if stall_count >= 3:
                        await _report(
                            f"Got {len(captured_posts)}/{needed} posts."
                        )
                        break
                    await page.evaluate("window.scrollTo(0, -500)")
                    await page.wait_for_timeout(2000)
                else:
                    stall_count = 0
        finally:
            await browser.close()

    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:needed]


async def find_post_id_by_title(title_query, channel_url=CHANNEL_URL,
                                max_search=2000, cancel_event=None,
                                progress_callback=None):
    """Find the most recent post whose text contains `title_query`.

    Walks the public Telegram channel page, scrolling to load older messages,
    and returns the first (most recent) post where the normalized post text
    contains the normalized query as a substring. Case-insensitive.

    Args:
        title_query: Title or unique fragment to match.
        channel_url: Public Telegram channel URL.
        max_search: Hard cap on number of posts scanned before giving up.
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        Tuple (numeric_id, matched_post_data) on success, or (None, None) if
        no match is found within max_search posts.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needle = _normalize_for_match(title_query)
    if not needle:
        return (None, None)

    processed_ids = set()
    scanned = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            await _report(f"Searching for article: {title_query[:60]}...")
            await page.goto(channel_url)
            await page.wait_for_selector(".tgme_widget_message", state="visible")

            stall_count = 0

            while scanned < max_search:
                if cancel_event and cancel_event.is_set():
                    break

                batch = await _extract_posts_from_page(page, processed_ids)

                # Scan newest-first within the batch so the most recent match
                # wins when multiple candidates share the page.
                ordered = sorted(
                    batch, key=lambda pair: pair[1] or 0, reverse=True
                )
                for post_data, numeric_id in ordered:
                    scanned += 1
                    haystack = _post_match_text(post_data)
                    if needle in haystack:
                        return (numeric_id, post_data)
                    if scanned >= max_search:
                        break

                if scanned >= max_search:
                    break

                await _report(
                    f"Searched {scanned}/{max_search} posts, scrolling..."
                )

                # Scroll up to load older messages
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)

                if not batch:
                    stall_count += 1
                    if stall_count >= 3:
                        await _report(
                            f"No more posts to search (scanned {scanned})."
                        )
                        break
                    await page.evaluate("window.scrollTo(0, -500)")
                    await page.wait_for_timeout(2000)
                else:
                    stall_count = 0
        finally:
            await browser.close()

    return (None, None)


async def scrape_forward_from(anchor_id, count, channel_url=CHANNEL_URL,
                              cancel_event=None, progress_callback=None,
                              chronological=False):
    """Scrape `count` posts starting at `anchor_id` and moving forward in time.

    The anchor post is included as the oldest item in the batch; the next
    `count - 1` newer posts follow. To handle deleted/missing post IDs, this
    over-requests by ~30% from the underlying ID-range scraper, then trims
    to `count` after sorting ascending by ID.

    Args:
        anchor_id: Numeric post ID to anchor on (included in batch).
        count: Total number of posts to return.
        channel_url: Public Telegram channel URL.
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.
        chronological: If True, return ascending (oldest first); else descending.

    Returns:
        List of post dicts (length up to `count`).
    """
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
        chronological=True,  # collect in canonical order, re-sort below
    )

    # Trim to exactly `count` posts ascending from the anchor, then apply
    # the caller's preferred direction.
    posts.sort(key=_post_sort_key)  # ascending (oldest first)
    posts = posts[:count]
    posts.sort(key=_post_sort_key, reverse=not chronological)
    return posts


async def scrape_by_post_ids(start_id, end_id, channel_url=CHANNEL_URL,
                             cancel_event=None, progress_callback=None,
                             chronological=False):
    """Scrape posts by actual Telegram post IDs (permanent, never change).

    Unlike scrape_range() which uses offsets from latest, this uses
    absolute post IDs. Post #35808 is always post #35808 regardless
    of how many new posts are published.

    Args:
        start_id: Newer post ID (larger number, e.g., 35808).
        end_id: Older post ID (smaller number, e.g., 35758).
        channel_url: Public Telegram channel URL.
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        List of post dicts, ordered newest-first.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    needed = start_id - end_id
    captured_posts = []
    processed_ids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            # Jump directly — no need to find latest post ID
            jump_url = f"{channel_url}?before={start_id + 1}"
            await _report(f"Jumping to post #{start_id}...")
            await page.goto(jump_url)

            try:
                await page.wait_for_selector(
                    ".tgme_widget_message", state="visible", timeout=10000
                )
            except Exception:
                await _report("No posts found at this ID.")
                return []

            stall_count = 0

            while len(captured_posts) < needed:
                if cancel_event and cancel_event.is_set():
                    break

                batch = await _extract_posts_from_page(page, processed_ids)
                added_this_round = 0

                for post_data, numeric_id in batch:
                    if numeric_id is None:
                        continue
                    # Only include posts within the requested ID range
                    if numeric_id >= end_id and numeric_id <= start_id:
                        captured_posts.append(post_data)
                        added_this_round += 1
                        if len(captured_posts) >= needed:
                            break

                if len(captured_posts) >= needed:
                    break

                await _report(
                    f"Collected {len(captured_posts)}/{needed} posts "
                    f"(#{start_id} to #{end_id})..."
                )

                # Scroll up to load older messages
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)

                if added_this_round == 0:
                    stall_count += 1
                    if stall_count >= 3:
                        await _report(
                            f"Got {len(captured_posts)}/{needed} posts."
                        )
                        break
                    await page.evaluate("window.scrollTo(0, -500)")
                    await page.wait_for_timeout(2000)
                else:
                    stall_count = 0
        finally:
            await browser.close()

    captured_posts.sort(key=_post_sort_key, reverse=not chronological)
    return captured_posts[:needed]
