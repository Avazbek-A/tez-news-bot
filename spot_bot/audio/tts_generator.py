import asyncio
import os
import tempfile
import time
import edge_tts
from spot_bot.config import DEFAULT_VOICE, TTS_RATE, MAX_CONCURRENT_TTS

# Timeout per article (seconds). Most articles finish in 5-15s.
PER_ARTICLE_TIMEOUT = 60

# Minimum interval between progress reports (seconds)
_PROGRESS_DEBOUNCE = 2.0


async def generate_audio(text, output_path, voice=DEFAULT_VOICE, rate=TTS_RATE):
    """Generate an MP3 file from text using Microsoft Edge TTS.

    Returns the output_path if successful, None on failure.
    """
    if not text or not text.strip():
        return None
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await asyncio.wait_for(communicate.save(output_path), timeout=PER_ARTICLE_TIMEOUT)
        return output_path
    except asyncio.TimeoutError:
        print(f"TTS timeout after {PER_ARTICLE_TIMEOUT}s, skipping")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
    except Exception as e:
        print(f"TTS error: {e}")
        return None


async def generate_batch(articles, voice=DEFAULT_VOICE, rate=TTS_RATE,
                         cancel_event=None, progress_callback=None):
    """Generate MP3 files for a list of articles using parallel workers.

    Uses MAX_CONCURRENT_TTS (default 4) parallel TTS calls for ~4x speedup.

    Args:
        articles: List of article dicts with 'title' and 'body' keys.
        voice: TTS voice name.
        rate: Speech rate adjustment.
        cancel_event: asyncio.Event to signal cancellation.
        progress_callback: Optional async callable(str) for status updates.

    Returns:
        List of (article, audio_path) tuples. audio_path is None if TTS failed.
    """
    async def _report(msg):
        if progress_callback:
            await progress_callback(msg)

    tmpdir = tempfile.mkdtemp(prefix="spot_tts_")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TTS)
    completed = 0
    last_report_time = 0.0
    total = len(articles)

    async def _generate_one(i, article):
        nonlocal completed, last_report_time

        if cancel_event and cancel_event.is_set():
            return (article, None)

        # Build speak text
        parts = []
        if article.get("title"):
            parts.append(article["title"])
        if article.get("body"):
            parts.append(article["body"])
        speak_text = "\n\n".join(parts)

        if not speak_text.strip():
            return (article, None)

        filename = f"article_{i + 1:03d}.mp3"
        output_path = os.path.join(tmpdir, filename)

        async with semaphore:
            if cancel_event and cancel_event.is_set():
                return (article, None)

            audio_path = await generate_audio(speak_text, output_path, voice, rate)
            completed += 1

            # Debounced progress reporting
            now = time.monotonic()
            if now - last_report_time >= _PROGRESS_DEBOUNCE:
                last_report_time = now
                await _report(f"Audio: {completed}/{total}...")

            return (article, audio_path)

    tasks = [_generate_one(i, a) for i, a in enumerate(articles)]
    results = await asyncio.gather(*tasks)

    successful = sum(1 for _, p in results if p)
    await _report(f"Audio done: {successful}/{total} files generated.")
    return list(results)


def combine_audio_files(results, output_path):
    """Concatenate individual MP3 files into one combined file.

    Binary MP3 concatenation works for CBR files (which edge-tts produces).

    Args:
        results: List of (article, audio_path) tuples.
        output_path: Path to write the combined MP3 file.

    Returns:
        The output_path if successful, None if no files to combine.
    """
    valid_paths = [p for _, p in results if p and os.path.exists(p)]
    if not valid_paths:
        return None

    with open(output_path, "wb") as out:
        for path in valid_paths:
            with open(path, "rb") as f:
                out.write(f.read())

    return output_path


async def combine_audio_with_announcements(results, output_path, voice=DEFAULT_VOICE,
                                           rate=TTS_RATE, announcement_prefix="Next article:",
                                           untitled_text="Untitled"):
    """Combine MP3 files with title announcements interleaved.

    Generates a short TTS clip saying "[prefix] [title]" before
    each article's audio, then binary-concatenates everything into one file.

    Args:
        results: List of (article, audio_path) tuples.
        output_path: Path to write the combined MP3 file.
        voice: TTS voice name (same as article audio).
        rate: TTS speech rate.
        announcement_prefix: Localized prefix (e.g. "Next article:").
        untitled_text: Localized fallback for articles without titles.

    Returns:
        The output_path if successful, None if no files to combine.
    """
    valid = [(article, path) for article, path in results
             if path and os.path.exists(path)]
    if not valid:
        return None

    tmpdir = os.path.dirname(output_path)
    announcement_paths = []

    try:
        # Generate announcement clips
        for i, (article, _) in enumerate(valid):
            title = (article.get("title") or "").strip() or untitled_text
            ann_text = f"{announcement_prefix} {title}"
            ann_path = os.path.join(tmpdir, f"announcement_{i:03d}.mp3")
            result = await generate_audio(ann_text, ann_path, voice, rate)
            announcement_paths.append(result)

        # Binary concatenation: announcement + article audio
        with open(output_path, "wb") as out:
            for i, (_, audio_path) in enumerate(valid):
                ann_path = announcement_paths[i]
                if ann_path and os.path.exists(ann_path):
                    with open(ann_path, "rb") as f:
                        out.write(f.read())
                with open(audio_path, "rb") as f:
                    out.write(f.read())

        return output_path

    finally:
        for ann_path in announcement_paths:
            if ann_path and os.path.exists(ann_path):
                try:
                    os.remove(ann_path)
                except OSError:
                    pass


def cleanup_audio_files(results, combined_path=None):
    """Remove temporary audio files after sending."""
    dirs_to_clean = set()
    for _, audio_path in results:
        if audio_path and os.path.exists(audio_path):
            dirs_to_clean.add(os.path.dirname(audio_path))
            os.remove(audio_path)
    if combined_path and os.path.exists(combined_path):
        os.remove(combined_path)
    for d in dirs_to_clean:
        try:
            os.rmdir(d)
        except OSError:
            pass
