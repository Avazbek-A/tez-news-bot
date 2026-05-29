"""Intentional post/article filters: skip already-seen + mute categories.

These are *user-chosen* filters, distinct from the transient-failure
handling in the scrapers. The guiding rule: intentional drops are fine,
but they must be **counted and reported** so the user always knows what
was filtered (never a silent loss).

Two stages:
- `filter_posts` runs pre-fetch on raw channel posts (dicts with `id` /
  `links` / `text_html`). It drops already-seen posts and posts whose
  spot.uz URL slug or caption matches a mute rule — cheaply, before the
  expensive article fetch.
- `mute_articles` is the post-fetch safety net: it re-checks the cleaned
  title + body so a muted item that slipped past the URL/caption check
  (or arrived via RSS, which has no Telegram caption) is still removed.
"""
from __future__ import annotations


# spot.uz publishes the daily exchange-rate post under this URL slug.
_CURRENCY_SLUGS = ("currency-exchange",)
# Title/caption/body markers for the same recurring currency posts, across
# the languages spot.uz / the channel use. Matched case-insensitively as
# substrings.
_CURRENCY_PATTERNS = (
    "курс валют",        # ru
    "обменный курс",     # ru (alt)
    "valyuta kurs",      # uz
    "currency rate",     # en
    "exchange rate",     # en (alt)
)


def _numeric_id(post_id) -> int | None:
    """Extract the trailing integer from a post id like 'spotuz/37764'."""
    try:
        return int(str(post_id).split("/")[-1])
    except (ValueError, IndexError, AttributeError):
        return None


def _matches_currency(text: str, links) -> bool:
    """True if the post looks like a recurring currency/exchange-rate post."""
    for link in links or []:
        low = (link or "").lower()
        if any(slug in low for slug in _CURRENCY_SLUGS):
            return True
    low_text = (text or "").lower()
    return any(pat in low_text for pat in _CURRENCY_PATTERNS)


def _matches_keywords(text: str, keywords) -> bool:
    """True if any muted keyword appears (case-insensitive) in `text`."""
    if not keywords:
        return False
    low = (text or "").lower()
    return any(kw and kw.lower() in low for kw in keywords)


def filter_posts(posts, *, delivered_ids=None, skip_seen=False,
                 mute_currency=False, muted_keywords=None):
    """Pre-fetch filter over raw channel posts.

    Args:
        posts: list of post dicts ({id, links, text_html, ...}).
        delivered_ids: iterable of numeric post IDs already delivered.
        skip_seen: when True, drop posts whose numeric id is in
            `delivered_ids`. (Caller is responsible for only enabling this
            in "latest" mode — explicit ranges should pass False.)
        mute_currency: when True, drop recurring currency/exchange posts.
        muted_keywords: list of substrings; a post whose caption/links
            contain any of them is dropped.

    Returns:
        (kept, skipped_seen_count, muted_count) — order of `kept` matches
        the input order.
    """
    delivered = set(delivered_ids or [])
    muted_keywords = muted_keywords or []

    kept = []
    skipped_seen = 0
    muted = 0

    for post in posts:
        if skip_seen and delivered:
            nid = _numeric_id(post.get("id"))
            if nid is not None and nid in delivered:
                skipped_seen += 1
                continue

        text = post.get("text_html", "")
        links = post.get("links", [])
        if mute_currency and _matches_currency(text, links):
            muted += 1
            continue
        if _matches_keywords(text, muted_keywords):
            muted += 1
            continue

        kept.append(post)

    return kept, skipped_seen, muted


def mute_articles(articles, *, mute_currency=False, muted_keywords=None):
    """Post-fetch safety net over cleaned articles ({title, body, ...}).

    Catches muted items whose Telegram caption/URL didn't trigger the
    pre-fetch filter (or that arrived via RSS). Returns (kept, muted_count).
    """
    muted_keywords = muted_keywords or []
    if not mute_currency and not muted_keywords:
        return list(articles), 0

    kept = []
    muted = 0
    for art in articles:
        # Only the title + a body head are needed; currency posts announce
        # themselves immediately.
        haystack = (art.get("title", "") or "") + " " + (art.get("body", "") or "")[:500]
        if mute_currency and _matches_currency(haystack, None):
            muted += 1
            continue
        if _matches_keywords(haystack, muted_keywords):
            muted += 1
            continue
        kept.append(art)

    return kept, muted
