"""High-level scrape → fetch → clean → filter → audio pipeline.

`run_pipeline()` orchestrates the three scrapers, the article fetcher,
text cleaning, per-user keyword filtering, and optional TTS. Each stage
reports progress via an async callback and honors a cancel event.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from spot_bot.ai.summarize import summarize_batch
from spot_bot.audio.tts_generator import generate_batch
from spot_bot.cleaners.text_cleaner import clean_batch
from spot_bot.config import CHANNEL_URL, DEFAULT_VOICE, TTS_RATE
from spot_bot.scrapers.article_fetcher import fetch_articles
from spot_bot.scrapers.telegram_channel import (
    scrape_by_post_ids,
    scrape_latest,
    scrape_range,
)
from spot_bot.storage import filters as filter_store
from spot_bot.storage import user_settings

logger = logging.getLogger(__name__)

# A progress callback receives a single status string and returns None.
ProgressCallback = Callable[[str], Awaitable[None]]

# One article as it flows through the pipeline. We model it as an open
# dict since stages add keys (source, images, audio_path) incrementally.
Article = dict[str, Any]


@dataclass
class PipelineResult:
    articles: list[Article] = field(default_factory=list)
    audio_results: list[tuple[Article, str | None]] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    filtered_count: int = 0  # articles dropped by user keyword filters


def _check_cancelled(cancel_event: asyncio.Event | None) -> None:
    """Raise CancelledError if the cancel event is set."""
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()


async def run_pipeline(
    count: int | None = None,
    start_offset: int | None = None,
    end_offset: int | None = None,
    start_post_id: int | None = None,
    end_post_id: int | None = None,
    include_audio: bool = False,
    include_images: bool = False,
    include_summary: bool = False,
    voice: str = DEFAULT_VOICE,
    rate: str = TTS_RATE,
    lang: str = "en",
    channel_url: str | None = None,
    cancel_event: asyncio.Event | None = None,
    progress_callback: ProgressCallback | None = None,
    user_id: int | None = None,
) -> PipelineResult:
    """Run the full scrape → fetch → clean → filter → audio pipeline.

    Exactly one of three scrape modes is chosen based on which args are set:
    - (start_post_id, end_post_id): scrape by absolute post IDs (inclusive)
    - (start_offset, end_offset): scrape by offset range from the latest post
    - otherwise: scrape `count` latest posts (default 20)

    Returns a PipelineResult whose `articles` have been cleaned and
    filtered. If `include_audio` and there are articles, `audio_results`
    holds (article, mp3_path) tuples; path is None when TTS failed.
    """

    async def _report(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    # Use per-user channel URL if none provided
    if channel_url is None:
        if user_id is not None:
            channel_url = await user_settings.get(user_id, "channel_url")
        else:
            channel_url = CHANNEL_URL

    # 1. Scrape posts — post IDs, offset range, or latest
    _check_cancelled(cancel_event)

    posts: list[Article]
    if start_post_id is not None and end_post_id is not None:
        await _report(f"Scraping posts #{start_post_id} to #{end_post_id}...")
        posts = await scrape_by_post_ids(
            start_post_id, end_post_id,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
    elif start_offset is not None and end_offset is not None:
        await _report(f"Scraping posts {start_offset}-{end_offset} from latest...")
        posts = await scrape_range(
            start_offset, end_offset,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
    else:
        count = count or 20
        await _report(f"Scraping {count} latest posts from Telegram...")
        posts = await scrape_latest(
            count,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )

    await _report(f"Found {len(posts)} posts.")

    if not posts:
        return PipelineResult()

    # 2. Fetch full article content
    _check_cancelled(cancel_event)
    await _report("Fetching full articles from spot.uz...")
    articles = await fetch_articles(
        posts, include_images=include_images,
        progress_callback=progress_callback,
    )
    await _report(f"Fetched {len(articles)} articles.")

    # 3. Clean text for reading/TTS. Offload to a worker thread so the
    #    event loop can keep serving progress updates / cancel signals
    #    while regex cleaning runs.
    _check_cancelled(cancel_event)
    await _report("Cleaning text...")
    articles = await asyncio.to_thread(clean_batch, articles)

    # Filter out articles with empty body, tracking what was removed
    skipped_ids: list[str] = []
    kept: list[Article] = []
    for a in articles:
        if a.get("body", "").strip():
            kept.append(a)
        else:
            post_id = a.get("id", "unknown")
            skipped_ids.append(post_id)
            logger.info("Filtered out article %s: empty body after cleaning", post_id)

    articles = kept
    if skipped_ids:
        await _report(f"Cleaned {len(articles)} articles ready ({len(skipped_ids)} empty).")
    else:
        await _report(f"Cleaned {len(articles)} articles ready.")

    # 3b. Apply per-user keyword filters
    filtered_count = 0
    if user_id is not None:
        include, exclude = await filter_store.get_sets(user_id)
        if include or exclude:
            articles, dropped = filter_store.apply_filters(articles, include, exclude)
            filtered_count = len(dropped)
            if filtered_count:
                logger.info("Keyword filters dropped %d article(s)", filtered_count)
                await _report(
                    f"Filtered {filtered_count} article(s) by your keyword rules."
                )

    # 3c. Optional AI summaries (adds `summary` key to each article).
    if include_summary and articles:
        _check_cancelled(cancel_event)
        await _report("Summarizing with Claude...")
        await summarize_batch(articles, lang=lang, progress_callback=progress_callback)

    result = PipelineResult(
        articles=articles,
        skipped_ids=skipped_ids,
        filtered_count=filtered_count,
    )

    # 4. Generate audio (optional)
    if include_audio and articles:
        _check_cancelled(cancel_event)
        await _report("Generating audio files...")
        result.audio_results = await generate_batch(
            articles, voice=voice, rate=rate,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )

    return result
