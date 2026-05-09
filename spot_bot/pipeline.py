import asyncio
from dataclasses import dataclass, field
from spot_bot.scrapers.telegram_channel import (
    scrape_latest,
    scrape_range,
    scrape_by_post_ids,
    find_post_id_by_title,
    scrape_forward_from,
    _post_first_line,
)
from spot_bot.scrapers.article_fetcher import fetch_articles
from spot_bot.cleaners.text_cleaner import clean_batch
from spot_bot.audio.tts_generator import generate_batch, cleanup_audio_files
from spot_bot.config import DEFAULT_VOICE, TTS_RATE
from spot_bot.settings import get_setting


@dataclass
class PipelineResult:
    articles: list = field(default_factory=list)
    audio_results: list = field(default_factory=list)
    # Populated when from_title resolution succeeds; useful for status messages.
    matched_title_preview: str = ""
    # Numeric post ID of the anchor article when from_title resolved a match.
    matched_post_id: int = 0
    # True when from_title was provided but no matching post was found.
    title_not_found: bool = False


def _check_cancelled(cancel_event):
    """Raise CancelledError if the cancel event is set."""
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()


async def run_pipeline(count=None, start_offset=None, end_offset=None,
                       start_post_id=None, end_post_id=None,
                       from_title=None, from_count=None,
                       forward_anchor_id=None,
                       title_search_depth=2000,
                       include_audio=False, include_images=False,
                       voice=DEFAULT_VOICE, rate=TTS_RATE,
                       channel_url=None, cancel_event=None,
                       progress_callback=None, chronological=False):
    """Run the full scrape -> fetch -> clean -> audio pipeline.

    Args:
        count: Number of latest posts to scrape (used when no range given).
        start_offset: Start of range from latest (e.g. 2000).
        end_offset: End of range from latest (e.g. 1950).
        start_post_id: Newer post ID for ID-based range (e.g. 35808).
        end_post_id: Older post ID for ID-based range (e.g. 35758).
        include_audio: Whether to generate MP3 audio files.
        include_images: Whether to extract article images.
        voice: TTS voice name.
        rate: TTS speech rate.
        channel_url: Override channel URL (defaults to saved setting).
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        PipelineResult with articles and optionally audio file paths.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    # Use saved channel URL if none provided
    if channel_url is None:
        channel_url = get_setting("channel_url")

    matched_title_preview = ""
    matched_post_id = 0

    # 1. Scrape posts — title-anchored, post IDs, offset range, or latest
    _check_cancelled(cancel_event)

    if forward_anchor_id is not None:
        # Bot layer already resolved a post ID (e.g. via user-confirmed
        # title search) — scrape forward without re-resolving.
        target_count = from_count or count or 50
        await _report(
            f"[1/4] Scraping {target_count} posts forward from #{forward_anchor_id}..."
        )
        posts = await scrape_forward_from(
            forward_anchor_id, target_count,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            chronological=chronological,
        )
        matched_post_id = forward_anchor_id
    elif from_title:
        # Resolve title to a post ID, then scrape forward from there.
        # (No confirmation step; used by non-interactive callers.)
        target_count = from_count or count or 50
        await _report(f"Searching for: {from_title[:60]}...")
        anchor_id, anchor_post = await find_post_id_by_title(
            from_title,
            channel_url=channel_url,
            max_search=title_search_depth,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
        if anchor_id is None:
            return PipelineResult(title_not_found=True)

        preview = _post_first_line(anchor_post) if anchor_post else ""
        await _report(
            f"Found post #{anchor_id}. Scraping next {target_count}..."
        )
        posts = await scrape_forward_from(
            anchor_id, target_count,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            chronological=chronological,
        )
        # Stash the preview + anchor ID for the caller's status messages
        matched_title_preview = preview
        matched_post_id = anchor_id
    elif start_post_id is not None and end_post_id is not None:
        await _report(f"[1/4] Scraping posts #{start_post_id} to #{end_post_id}...")
        posts = await scrape_by_post_ids(
            start_post_id, end_post_id,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            chronological=chronological,
        )
    elif start_offset is not None and end_offset is not None:
        needed = start_offset - end_offset
        await _report(f"[1/4] Scraping posts {start_offset}-{end_offset} from latest...")
        posts = await scrape_range(
            start_offset, end_offset,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            chronological=chronological,
        )
    else:
        count = count or 20
        await _report(f"[1/4] Scraping {count} latest posts from Telegram...")
        posts = await scrape_latest(
            count,
            channel_url=channel_url,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            chronological=chronological,
        )

    await _report(f"[1/4] Found {len(posts)} posts.")

    if not posts:
        return PipelineResult(
            matched_title_preview=matched_title_preview,
            matched_post_id=matched_post_id,
        )

    # 2. Fetch full article content
    _check_cancelled(cancel_event)
    await _report("[2/4] Fetching full articles from spot.uz...")
    articles = await fetch_articles(
        posts, include_images=include_images,
        progress_callback=progress_callback,
        stage_prefix="[2/4] ",
    )
    await _report(f"[2/4] Fetched {len(articles)} articles.")

    # 3. Clean text for reading/TTS
    _check_cancelled(cancel_event)
    await _report("[3/4] Cleaning text...")
    articles = clean_batch(articles)

    # Filter out articles with empty body
    articles = [a for a in articles if a.get("body", "").strip()]
    await _report(f"[3/4] Cleaned {len(articles)} articles ready.")

    result = PipelineResult(
        articles=articles,
        matched_title_preview=matched_title_preview,
        matched_post_id=matched_post_id,
    )

    # 4. Generate audio (optional)
    if include_audio and articles:
        _check_cancelled(cancel_event)
        await _report("[4/4] Generating audio files...")

        async def _audio_progress(msg):
            if progress_callback:
                await progress_callback(f"[4/4] {msg}")

        result.audio_results = await generate_batch(
            articles, voice=voice, rate=rate,
            cancel_event=cancel_event,
            progress_callback=_audio_progress,
        )

    return result
