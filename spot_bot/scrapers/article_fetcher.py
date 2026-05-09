import asyncio
import time
from playwright.async_api import async_playwright
from spot_bot.config import MAX_CONCURRENT_FETCHES, USER_AGENT
from spot_bot.cleaners.html_cleaner import clean_html, clean_telegram_text


# Minimum interval between progress reports (seconds), matched to TTS pacing.
_PROGRESS_DEBOUNCE = 2.0


async def fetch_articles(posts, include_images=False, progress_callback=None,
                         stage_prefix=""):
    """Fetch full article content for posts that link to spot.uz.

    For posts without a spot.uz link, uses the Telegram post text directly.

    Args:
        posts: List of post dicts from the scraper.
        include_images: If True, extract article images (slower).
        progress_callback: Optional async callable(str) for status updates.
        stage_prefix: Optional prefix for progress messages (e.g. "[2/5] ").

    Returns:
        List of article dicts with keys: title, body, date, source, images.
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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)

        tasks = [
            _process_post(
                context, post, semaphore, include_images,
                progress_one=_progress_one,
            )
            for post in posts
        ]

        # Use asyncio.gather; per-task progress is reported via _progress_one
        # as each task finishes its work.
        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Fetch error: {result}")
                continue
            if result:
                articles.append(result)

        await browser.close()

    await _report(f"Fetched {len(articles)}/{total} articles.")
    return articles


async def _process_post(context, post, semaphore, include_images=False,
                        progress_one=None):
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

    # No spot.uz link — use Telegram text directly
    if not link:
        await _tick()
        return {
            "title": "",
            "body": telegram_text,
            "date": date,
            "source": "telegram",
            "images": [],
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
                await page.goto(link, timeout=30000, wait_until="domcontentloaded")
                try:
                    await page.wait_for_selector(".contentBox", timeout=5000)
                except Exception:
                    pass  # Proceed anyway

                content = await page.content()
            except Exception as nav_e:
                print(f"Nav error for {link}: {nav_e}")
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

            return {
                "title": headline or "",
                "body": body,
                "date": date,
                "source": "spot.uz",
                "images": images if include_images else [],
            }

        except Exception as e:
            print(f"Error fetching {post.get('id')}: {e}")
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
            await _tick()
