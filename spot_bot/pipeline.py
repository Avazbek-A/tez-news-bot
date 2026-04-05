import asyncio
from dataclasses import dataclass, field
from spot_bot.scrapers.telegram_channel import scrape_latest, scrape_range
from spot_bot.scrapers.article_fetcher import fetch_articles
from spot_bot.cleaners.text_cleaner import clean_batch
from spot_bot.audio.tts_generator import generate_batch, cleanup_audio_files
from spot_bot.config import DEFAULT_VOICE, TTS_RATE
from spot_bot.settings import get_setting


@dataclass
class PipelineResult:
    articles: list = field(default_factory=list)
    audio_results: list = field(default_factory=list)


def _check_cancelled(cancel_event):
    """Raise CancelledError if the cancel event is set."""
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()


async def run_pipeline(count=None, start_offset=None, end_offset=None,
                       include_audio=False, include_images=False,
                       voice=DEFAULT_VOICE, rate=TTS_RATE,
                       channel_url=None, cancel_event=None,
                       progress_callback=None):
    """Run the full scrape -> fetch -> clean -> audio pipeline.

    Args:
        count: Number of latest posts to scrape (used when no range given).
        start_offset: Start of range from latest (e.g. 2000).
        end_offset: End of range from latest (e.g. 1950).
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

    # 1. Scrape posts — range or latest
    _check_cancelled(cancel_event)

    if start_offset is not None and end_offset is not None:
        needed = start_offset - end_offset
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

    # 3. Clean text for reading/TTS
    _check_cancelled(cancel_event)
    await _report("Cleaning text...")
    articles = clean_batch(articles)

    # Filter out articles with empty body
    articles = [a for a in articles if a.get("body", "").strip()]
    await _report(f"Cleaned {len(articles)} articles ready.")

    result = PipelineResult(articles=articles)

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
