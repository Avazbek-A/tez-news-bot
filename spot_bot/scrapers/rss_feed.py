"""RSS / Atom feed scraper.

Returns the same article-dict shape as the Telegram channel scraper so the
rest of the pipeline (cleaning, TTS, delivery) doesn't need to know which
source the article came from.

Article dict shape:
    {
        "id": "<source_id>/<entry_id_or_hash>",
        "title": str,
        "body": str (cleaned plain text from the entry's content/summary),
        "date": ISO-8601 date string or "",
        "source": "rss",
        "images": [],   # not extracted in v1
    }
"""

import asyncio
import hashlib
import time
from datetime import datetime

from spot_bot.cleaners.html_cleaner import clean_telegram_text as _html_to_text


def _entry_id(entry, source_id):
    """Build a stable, source-prefixed id for a feed entry."""
    raw = (
        getattr(entry, "id", None)
        or getattr(entry, "guid", None)
        or getattr(entry, "link", None)
        or ""
    )
    if not raw:
        # Last-resort: hash title+published
        raw = (
            (getattr(entry, "title", "") or "")
            + "|"
            + str(getattr(entry, "published", ""))
        )
    digest = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"{source_id}/{digest}"


def _entry_body(entry):
    """Pull the most informative content out of a feedparser entry, then
    strip HTML to plain text."""
    raw = ""
    content_list = getattr(entry, "content", None)
    if content_list:
        try:
            raw = content_list[0].value or ""
        except (IndexError, AttributeError):
            raw = ""
    if not raw:
        raw = getattr(entry, "summary", "") or ""
    if not raw:
        raw = getattr(entry, "description", "") or ""
    return _html_to_text(raw).strip()


def _entry_date(entry):
    """Return an ISO-8601 date string for the entry, or empty string."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        struct = getattr(entry, attr, None)
        if struct:
            try:
                return datetime(*struct[:6]).date().isoformat()
            except Exception:
                pass
    return ""


async def fetch_rss_articles(source_id, feed_url, count, cancel_event=None,
                             progress_callback=None, chronological=False):
    """Fetch up to `count` recent entries from an RSS/Atom feed.

    feedparser is synchronous; we run it in a thread so the bot's event
    loop isn't blocked during the network read + parse.
    """
    async def _report(msg):
        if progress_callback:
            try:
                await progress_callback(msg)
            except Exception:
                pass

    if cancel_event and cancel_event.is_set():
        return []

    await _report(f"[1/4] Fetching RSS: {source_id}...")

    def _parse():
        # feedparser handles HTTP, redirects, encoding, conditional GETs.
        import feedparser
        return feedparser.parse(feed_url, agent="tez-news-bot/1.0")

    parsed = await asyncio.to_thread(_parse)

    if getattr(parsed, "bozo", 0) and not getattr(parsed, "entries", None):
        await _report(f"RSS error for {source_id}: {parsed.bozo_exception}")
        return []

    entries = list(parsed.entries or [])
    # Most feeds list newest-first already, but normalize: sort by parsed
    # date desc, with feeds that lack dates retaining input order.
    def _sort_key(e):
        for attr in ("published_parsed", "updated_parsed", "created_parsed"):
            s = getattr(e, attr, None)
            if s:
                return time.mktime(s)
        return 0.0
    entries.sort(key=_sort_key, reverse=True)
    entries = entries[:count]

    articles = []
    for entry in entries:
        body = _entry_body(entry)
        if not body.strip():
            continue
        articles.append({
            "id": _entry_id(entry, source_id),
            "title": (getattr(entry, "title", "") or "").strip(),
            "body": body,
            "date": _entry_date(entry),
            "source": "rss",
            "images": [],
            # Preserve original link for any future "open in browser" UX.
            "link": getattr(entry, "link", "") or "",
        })

    if not chronological:
        # Caller wants newest-first (default). Already that way; no-op.
        pass
    else:
        articles.reverse()

    await _report(
        f"[1/4] RSS {source_id}: collected {len(articles)} of {len(parsed.entries or [])}."
    )
    return articles
