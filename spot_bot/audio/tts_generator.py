import asyncio
import os
import re
import tempfile
import time
import edge_tts
from spot_bot.config import DEFAULT_VOICE, TTS_RATE, MAX_CONCURRENT_TTS

import logging
logger = logging.getLogger(__name__)

# Timeout per article (seconds). Most articles finish in 5-15s.
PER_ARTICLE_TIMEOUT = 60

# Long bodies (>TTS_CHUNK_CHAR_LIMIT chars) are split into chunks before TTS,
# then binary-concatenated. Edge TTS's WebSocket connection becomes flaky on
# very long inputs, so chunking is what keeps long interview-format articles
# from being silently dropped from combined audio output.
TTS_CHUNK_CHAR_LIMIT = 3000

# Conservative TTS speed (chars/sec) for computing per-chunk timeouts.
TTS_CHARS_PER_SECOND = 40

# Minimum interval between progress reports (seconds)
_PROGRESS_DEBOUNCE = 2.0


def _split_text_into_chunks(text, limit=TTS_CHUNK_CHAR_LIMIT):
    """Split long text into chunks <= `limit` chars at natural boundaries.

    Strategy (in order):
      1. Pack paragraphs (split on \\n\\n) greedily into chunks.
      2. If a single paragraph exceeds `limit`, split it on sentence
         boundaries (. / ! / ? followed by whitespace).
      3. If a single sentence still exceeds `limit`, split on whitespace
         at the limit boundary as a last resort.

    Returns a list of non-empty chunks.
    """
    if not text:
        return []

    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    # Step 1: split on paragraph boundaries
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Pre-split any oversize paragraphs into sentences/words
    pieces = []
    for para in paragraphs:
        if len(para) <= limit:
            pieces.append(para)
            continue

        # Step 2: sentence split
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) <= limit:
                pieces.append(sent)
                continue

            # Step 3: word-level fallback
            words = sent.split()
            buf = ""
            for w in words:
                candidate = (buf + " " + w).strip() if buf else w
                if len(candidate) > limit and buf:
                    pieces.append(buf)
                    buf = w
                else:
                    buf = candidate
            if buf:
                pieces.append(buf)

    # Greedily pack pieces into chunks <= limit, preserving boundaries.
    chunks = []
    buf = ""
    for piece in pieces:
        if not buf:
            buf = piece
            continue
        candidate = buf + "\n\n" + piece
        if len(candidate) <= limit:
            buf = candidate
        else:
            chunks.append(buf)
            buf = piece
    if buf:
        chunks.append(buf)

    return [c for c in chunks if c.strip()]


async def _tts_to_file(text, output_path, voice, rate, timeout):
    """Single edge-tts call with timeout. Returns output_path or None."""
    if not text or not text.strip():
        return None
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await asyncio.wait_for(communicate.save(output_path), timeout=timeout)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        return None
    except asyncio.TimeoutError:
        logger.warning(f"TTS timeout after {timeout}s on {len(text)}-char chunk, skipping")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None
    except Exception as e:
        logger.warning(f"TTS error: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None


async def generate_audio(text, output_path, voice=DEFAULT_VOICE, rate=TTS_RATE,
                         cancel_event=None):
    """Generate an MP3 file from text using the configured TTS engine.

    Default engine: Microsoft Edge TTS (free, online, decent quality).
    Optional alternative: Piper TTS (open-source, local, offline) — gated
    by /voice_engine piper. Piper falls back to Edge if its model files
    aren't present.

    For texts <= TTS_CHUNK_CHAR_LIMIT chars: single TTS call (fast path).
    For longer texts: split into chunks, generate each, binary-concat the
    resulting MP3s into output_path.

    Returns the output_path if at least one chunk succeeded, None otherwise.
    """
    if not text or not text.strip():
        return None

    # Engine selection. Order:
    # - voice_engine = "supertonic" → route by detected language: Supertonic
    #   for languages it supports (RU/EN/29 others), Edge TTS for the rest
    #   (Uzbek). Fully open-source for the bulk of articles.
    # - voice_engine = "piper" → use Piper if its model files are present
    #   (Phase 10 scaffold). Otherwise Edge TTS.
    # - default = Edge TTS (Microsoft online, free).
    try:
        from spot_bot.settings import get_setting
        engine = (get_setting("voice_engine") or "edge").lower()
    except Exception:
        engine = "edge"

    if engine == "supertonic":
        from spot_bot.audio.supertonic_engine import (
            supertonic_supports, generate_audio_supertonic,
        )
        from spot_bot.audio.lang_detect import detect_language
        detected = detect_language(text)
        if supertonic_supports(detected):
            result = await generate_audio_supertonic(
                text, output_path, lang=detected, speed_rate=rate,
            )
            if result:
                return result
            logger.warning(
                "[tts] Supertonic returned None for %s text; falling back to Edge",
                detected,
            )
        # else: language unsupported by Supertonic (e.g. Uzbek) → fall through
    elif engine == "piper":
        from spot_bot.audio.piper_engine import (
            piper_available, generate_audio_piper,
        )
        if piper_available():
            from spot_bot.settings import get_setting
            lang = get_setting("language") or "en"
            return await generate_audio_piper(
                text, output_path, lang=lang, speed_rate=rate,
            )

    # Fast path — short text, behave exactly as before
    if len(text) <= TTS_CHUNK_CHAR_LIMIT:
        return await _tts_to_file(text, output_path, voice, rate,
                                  PER_ARTICLE_TIMEOUT)

    # Long path — chunk, generate per-chunk, binary-concat
    chunks = _split_text_into_chunks(text)
    if not chunks:
        return None

    out_dir = os.path.dirname(output_path) or "."
    chunk_paths = []
    successes = 0

    try:
        for i, chunk in enumerate(chunks):
            if cancel_event and cancel_event.is_set():
                break

            chunk_path = os.path.join(
                out_dir,
                f".{os.path.basename(output_path)}.chunk_{i:03d}.mp3",
            )
            timeout = max(
                PER_ARTICLE_TIMEOUT,
                len(chunk) // TTS_CHARS_PER_SECOND + 15,
            )
            result = await _tts_to_file(chunk, chunk_path, voice, rate, timeout)
            if result:
                chunk_paths.append(chunk_path)
                successes += 1
            else:
                logger.warning(
                    "TTS chunk %d/%d failed (%d chars), continuing",
                    i + 1, len(chunks), len(chunk),
                )

        if not chunk_paths:
            return None

        # Binary-concat chunk MP3s into the final output_path.
        # edge-tts produces concat-safe CBR streams (same property already
        # exploited by combine_audio_files below).
        with open(output_path, "wb") as out:
            for p in chunk_paths:
                with open(p, "rb") as f:
                    out.write(f.read())

        if successes < len(chunks):
            logger.warning(
                "TTS partial: %d/%d chunks succeeded for %s",
                successes, len(chunks), output_path,
            )

        return output_path

    finally:
        for p in chunk_paths:
            try:
                os.remove(p)
            except OSError:
                pass


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

            audio_path = await generate_audio(
                speak_text, output_path, voice, rate,
                cancel_event=cancel_event,
            )
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
