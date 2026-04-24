"""Shared Playwright browser / context for the lifetime of the bot process.

Previously every scrape operation did `async with async_playwright()` which
launches Chromium and creates a fresh driver each time — 100-500ms of pure
overhead per call. This module keeps a single browser alive and hands out
short-lived pages via `page()` (an async context manager).

Call `shutdown()` from the bot's shutdown hook to clean up gracefully.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from spot_bot.config import USER_AGENT

logger = logging.getLogger(__name__)


_pw: Playwright | None = None
_browser: Browser | None = None
_context: BrowserContext | None = None
_lock = asyncio.Lock()


async def _ensure_started() -> BrowserContext:
    global _pw, _browser, _context
    if _context is not None:
        return _context
    async with _lock:
        # Double-checked locking — another coroutine may have initialized
        # while we awaited the lock.
        if _context is not None:
            return _context
        logger.info("Launching shared Playwright browser")
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
        _context = await _browser.new_context(user_agent=USER_AGENT)
        return _context


async def get_context() -> BrowserContext:
    """Return the shared BrowserContext, starting it on first call."""
    return await _ensure_started()


@asynccontextmanager
async def page() -> AsyncIterator[Any]:
    """Open a fresh page in the shared context; close it on exit.

    Usage:
        async with page() as p:
            await p.goto(url)
    """
    ctx = await _ensure_started()
    pg = await ctx.new_page()
    try:
        yield pg
    finally:
        try:
            await pg.close()
        except Exception as e:
            logger.warning("Error closing page: %s", e)


async def shutdown() -> None:
    """Close the shared browser. Safe to call multiple times or when never started."""
    global _pw, _browser, _context
    if _context is None:
        return
    logger.info("Shutting down shared Playwright browser")
    try:
        if _context is not None:
            await _context.close()
        if _browser is not None:
            await _browser.close()
        if _pw is not None:
            await _pw.stop()
    except Exception as e:
        logger.warning("Error during browser shutdown: %s", e)
    finally:
        _context = None
        _browser = None
        _pw = None
