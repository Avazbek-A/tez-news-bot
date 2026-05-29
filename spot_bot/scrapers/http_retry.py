"""Shared HTTP fetch-with-retry for the scrapers.

Both the channel-page walker (`telegram_channel`) and the article fetcher
(`article_fetcher`) need the same resilient GET: retry transient network
errors, timeouts, and retryable HTTP statuses (429 rate-limit, 5xx) with
exponential backoff + jitter, honoring any `Retry-After` header, while
bailing immediately on permanent statuses (404/403). Giving up early
silently drops news, so the policy leans toward more attempts.

This module is the single source of truth for that policy.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

import httpx

# Transient statuses worth retrying. 404/403/410 etc. are permanent for a
# given URL, so retrying them only wastes attempts.
DEFAULT_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

_logger = logging.getLogger(__name__)


def backoff_seconds(attempt: int, *, max_backoff: float = 10.0) -> float:
    """Exponential backoff with jitter: ~0.5, 1, 2, 4, 8s (+jitter), capped."""
    base = min(max_backoff, 0.5 * (2 ** attempt))
    return base + random.uniform(0, 0.4)


def retry_after_seconds(resp: httpx.Response, attempt: int, *,
                        max_backoff: float = 10.0) -> float:
    """Honor a server-sent Retry-After header (429/503), else use backoff."""
    ra = resp.headers.get("Retry-After")
    if ra:
        try:
            return min(max_backoff * 3, float(ra))
        except (ValueError, TypeError):
            pass
    return backoff_seconds(attempt, max_backoff=max_backoff)


async def fetch_text_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    retries: int = 5,
    retryable_status=None,
    max_backoff: float = 10.0,
    logger: logging.Logger = None,
    label: str = "Fetch",
) -> Optional[str]:
    """GET `url`, returning the response body text, or None on failure.

    Total attempts = `retries` + 1. Retries network errors, timeouts, and
    `retryable_status` codes with backoff + jitter (and Retry-After).
    Returns the body text on HTTP 200 (which may be an empty string — the
    caller decides whether empty counts as failure). Returns None on a
    permanent status or once the retry budget is exhausted.
    """
    log = logger or _logger
    retryable = retryable_status or DEFAULT_RETRYABLE_STATUS
    last_problem: Optional[str] = None

    for attempt in range(retries + 1):
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in retryable and attempt < retries:
                delay = retry_after_seconds(resp, attempt, max_backoff=max_backoff)
                log.warning(
                    "%s HTTP %d for %s — retry %d/%d in %.1fs",
                    label, resp.status_code, url, attempt + 1, retries, delay,
                )
                await asyncio.sleep(delay)
                last_problem = f"HTTP {resp.status_code}"
                continue
            log.warning("%s returned HTTP %d for %s", label, resp.status_code, url)
            return None
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_problem = repr(e)
            if attempt < retries:
                delay = backoff_seconds(attempt, max_backoff=max_backoff)
                log.warning(
                    "%s error for %s (%s) — retry %d/%d in %.1fs",
                    label, url, e, attempt + 1, retries, delay,
                )
                await asyncio.sleep(delay)
                continue

    if last_problem is not None:
        log.warning(
            "%s gave up on %s after %d attempts: %s",
            label, url, retries + 1, last_problem,
        )
    return None
