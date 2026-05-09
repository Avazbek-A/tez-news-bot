import asyncio
import os
import tempfile
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from spot_bot.config import TELEGRAM_MESSAGE_LIMIT
from spot_bot.audio.voice import (
    convert_mp3_to_opus,
    concat_mp3_to_opus,
    get_audio_duration,
    split_results_for_voice,
    compute_chapters,
    format_timestamp,
    ffmpeg_available,
    VOICE_MAX_DURATION_SECONDS,
)
from spot_bot.translations import t


# Telegram voice-message size cap from bots is 50MB (same as documents).
_VOICE_MAX_BYTES = 50 * 1024 * 1024

# Max chars for the per-voice-message caption (Telegram allows up to 1024,
# but a short caption keeps the chat scannable for navigation).
_VOICE_CAPTION_MAX = 80


def _short_caption(title: str, fallback_body: str = "") -> str:
    """Build a short, single-line caption from an article title."""
    text = (title or "").strip()
    if not text and fallback_body:
        text = fallback_body.strip().split("\n", 1)[0]
    text = text.replace("\n", " ").strip()
    if len(text) > _VOICE_CAPTION_MAX:
        text = text[: _VOICE_CAPTION_MAX - 1].rstrip() + "…"
    return text


async def send_articles_as_text(bot: Bot, chat_id: int, articles: list,
                                bookmark_label: str = "🔖 Save"):
    """Send cleaned articles as Telegram messages.

    Splits long articles at paragraph boundaries to stay within
    Telegram's 4096-char limit. The final chunk of each article
    carries an inline "🔖 Save" button so the user can bookmark.
    """
    for i, article in enumerate(articles):
        title = article.get("title", "")
        body = article.get("body", "")
        date = article.get("date", "")

        # Post ID
        post_id = ""
        raw_id = article.get("id", "")
        if "/" in raw_id:
            post_id = raw_id.split("/")[-1]

        # Format the message
        header = ""
        if title:
            header = f"<b>{_escape_html(title)}</b>\n"
        if date:
            header += f"<i>{date}</i>\n"
        if header:
            header += "\n"

        footer = ""
        if post_id:
            footer = f"\n\n<i>#{post_id}</i>"

        full_text = header + _escape_html(body) + footer

        # Build a save button if we have a numeric post ID; attach to the
        # final chunk only (multi-chunk articles otherwise duplicate it).
        save_kb = None
        if post_id and post_id.isdigit():
            save_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    bookmark_label,
                    callback_data=f"bookmark_{post_id}",
                ),
            ]])

        # Split and send
        chunks = _split_message(full_text, TELEGRAM_MESSAGE_LIMIT)
        last_idx = len(chunks) - 1
        for idx, chunk in enumerate(chunks):
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                reply_markup=save_kb if idx == last_idx else None,
            )
            await asyncio.sleep(0.3)  # Rate limiting


async def send_articles_as_file(bot: Bot, chat_id: int, articles: list,
                                filename: str = "Spot_News.txt"):
    """Send cleaned articles as a .txt document attachment.

    Builds a plain text file with all articles separated by dividers
    and sends it as a Telegram document.
    """
    lines = []
    for i, article in enumerate(articles):
        title = article.get("title", "")
        body = article.get("body", "")
        date = article.get("date", "")

        # Post ID
        post_id = ""
        raw_id = article.get("id", "")
        if "/" in raw_id:
            post_id = raw_id.split("/")[-1]

        if title:
            lines.append(title)
        if date:
            lines.append(f"Date: {date}")
        if title or date:
            lines.append("")
        if body:
            lines.append(body)
        if post_id:
            lines.append(f"\n#{post_id}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    content = "\n".join(lines)

    # Write to temp file and send
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="spot_news_", delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(content)
        tmp.close()

        with open(tmp.name, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=filename,
            )
    finally:
        os.unlink(tmp.name)


async def send_article_images(bot: Bot, chat_id: int, articles: list):
    """Send article images as Telegram photos.

    For each article that has images, sends them grouped after the article.
    Skips on failure (URL might be dead).
    """
    sent = 0
    for article in articles:
        images = article.get("images", [])
        if not images:
            continue

        title = article.get("title", "")

        for img in images:
            url = img.get("url", "")
            if not url:
                continue
            try:
                caption = img.get("alt", "") or title
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=url,
                    caption=caption[:200] if caption else None,
                )
                sent += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Error sending image {url}: {e}")

    return sent


async def send_voice_messages(bot: Bot, chat_id: int, results: list):
    """Send each article's audio as a Telegram voice message.

    Voice messages give native mobile playback speed control (1x/1.5x/2x).
    The TTS pipeline produces MP3; we convert each to OGG/Opus via ffmpeg
    before sending. Each voice message is capped at VOICE_MAX_DURATION_SECONDS;
    articles longer than that get split across multiple voice messages.

    Args:
        bot: Telegram Bot instance.
        chat_id: Chat to send to.
        results: List of (article, audio_path) tuples from TTS generator.

    Returns:
        Number of voice messages successfully sent.
    """
    has_ffmpeg = ffmpeg_available()
    print(
        f"[voice] entering send_voice_messages, "
        f"n_results={len(results)}, ffmpeg={has_ffmpeg}",
        flush=True,
    )
    if not has_ffmpeg:
        print(
            "[voice] ffmpeg not on PATH — falling back to music-track audio "
            "(no mobile speed control)."
        )
        return await _send_audio_fallback(bot, chat_id, results)

    sent = 0
    for article, mp3_path in results:
        if not mp3_path or not os.path.exists(mp3_path):
            continue

        # Convert mp3 -> ogg/opus next to the mp3 (cleanup_audio_files
        # removes the parent dir, so this gets cleaned automatically).
        ogg_path = mp3_path[:-4] + ".ogg" if mp3_path.endswith(".mp3") \
            else mp3_path + ".ogg"
        out_path = await convert_mp3_to_opus(mp3_path, ogg_path)
        if not out_path:
            print(f"Voice convert failed for {mp3_path}, skipping")
            continue

        duration = await get_audio_duration(out_path)
        # Within-article splitting if a single article exceeds the cap
        # (very rare — would be a 60+ min interview).
        if duration > VOICE_MAX_DURATION_SECONDS:
            print(
                f"Article voice exceeds {VOICE_MAX_DURATION_SECONDS}s "
                f"({duration:.0f}s); splitting"
            )
            sub_count = await _send_voice_split(
                bot, chat_id, out_path, article,
                total_duration=duration,
            )
            sent += sub_count
            try:
                os.remove(out_path)
            except OSError:
                pass
            continue

        try:
            file_size = os.path.getsize(out_path)
            if file_size > _VOICE_MAX_BYTES:
                print(f"Voice file too large ({file_size} bytes), skipping")
                continue

            caption = _short_caption(
                article.get("title", ""),
                fallback_body=article.get("body", ""),
            )

            with open(out_path, "rb") as f:
                await bot.send_voice(
                    chat_id=chat_id,
                    voice=f,
                    duration=int(duration) if duration > 0 else None,
                    caption=caption or None,
                )
            sent += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error sending voice message: {e}")
        finally:
            try:
                os.remove(out_path)
            except OSError:
                pass

    return sent


async def send_combined_voice(bot: Bot, chat_id: int, results: list,
                              status_callback=None, lang: str = "en"):
    """Send TTS results as one or more combined voice messages, splitting
    at VOICE_MAX_DURATION_SECONDS boundaries so each message stays within
    Telegram's 1-hour voice-message cap.

    Args:
        bot: Telegram Bot instance.
        chat_id: Chat to send to.
        results: List of (article, mp3_path) tuples from TTS generator.
        status_callback: Optional async callable(str) for progress updates.

    Returns:
        Number of underlying article-mp3s successfully delivered.
    """
    has_ffmpeg = ffmpeg_available()
    print(
        f"[voice] entering send_combined_voice, "
        f"n_results={len(results)}, ffmpeg={has_ffmpeg}",
        flush=True,
    )
    if not has_ffmpeg:
        print(
            "[voice] ffmpeg not on PATH — falling back to per-article "
            "music-track audio for combined mode."
        )
        return await _send_audio_fallback(bot, chat_id, results)

    async def _report(msg):
        if status_callback:
            try:
                await status_callback(msg)
            except Exception:
                pass

    batches = await split_results_for_voice(results)
    if not batches:
        return 0

    total_articles = sum(1 for _, p in results if p and os.path.exists(p))
    delivered = 0
    tmpdir = tempfile.mkdtemp(prefix="spot_voice_")

    try:
        for i, batch in enumerate(batches):
            mp3_paths = [p for _, p in batch if p and os.path.exists(p)]
            if not mp3_paths:
                continue

            await _report(
                f"Encoding voice part {i + 1}/{len(batches)}..."
            )

            ogg_path = os.path.join(tmpdir, f"combined_{i + 1:02d}.ogg")
            out = await concat_mp3_to_opus(mp3_paths, ogg_path)
            if not out:
                continue

            duration = await get_audio_duration(out)
            if os.path.getsize(out) > _VOICE_MAX_BYTES:
                print(
                    f"Combined voice part {i + 1} exceeds size cap, skipping"
                )
                try:
                    os.remove(out)
                except OSError:
                    pass
                continue

            try:
                await _report(
                    f"Sending voice part {i + 1}/{len(batches)}..."
                )
                # Caption: lead article title + part info, kept short.
                lead_article = batch[0][0] if batch else {}
                lead_title = _short_caption(
                    lead_article.get("title", ""),
                    fallback_body=lead_article.get("body", ""),
                )
                if len(batches) > 1:
                    suffix = f"  ·  Part {i + 1}/{len(batches)} ({len(mp3_paths)} articles)"
                else:
                    suffix = f"  ·  {len(mp3_paths)} articles" if len(mp3_paths) > 1 else ""
                caption_text = (lead_title + suffix).strip() or None

                with open(out, "rb") as f:
                    await bot.send_voice(
                        chat_id=chat_id,
                        voice=f,
                        duration=int(duration) if duration > 0 else None,
                        caption=caption_text,
                    )
                delivered += len(mp3_paths)
                await asyncio.sleep(0.5)

                # Chapter table-of-contents text message (only when there
                # are multiple articles to navigate between in this part).
                if len(batch) > 1:
                    try:
                        chapters = await compute_chapters(batch)
                        if chapters:
                            await _send_chapter_list(bot, chat_id, chapters, lang)
                    except Exception as e:
                        print(f"Chapter list send failed: {e}")
            except Exception as e:
                print(f"Error sending combined voice part {i + 1}: {e}")
            finally:
                try:
                    os.remove(out)
                except OSError:
                    pass
    finally:
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    return delivered


async def _send_voice_split(bot, chat_id, ogg_path, article, total_duration):
    """Split an over-long voice file into ≤VOICE_MAX_DURATION_SECONDS chunks
    via ffmpeg, then send each chunk."""
    chunk_dir = tempfile.mkdtemp(prefix="spot_voice_split_")
    sent = 0
    try:
        chunk_seconds = VOICE_MAX_DURATION_SECONDS
        n_chunks = int(total_duration // chunk_seconds) + 1
        for idx in range(n_chunks):
            start = idx * chunk_seconds
            chunk_path = os.path.join(chunk_dir, f"chunk_{idx:02d}.ogg")
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", ogg_path,
                "-ss", str(start),
                "-t", str(chunk_seconds),
                "-c", "copy",
                chunk_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=120)
            except asyncio.TimeoutError:
                proc.kill()
                continue

            if not os.path.exists(chunk_path) or os.path.getsize(chunk_path) == 0:
                continue
            if os.path.getsize(chunk_path) > _VOICE_MAX_BYTES:
                continue

            try:
                dur = await get_audio_duration(chunk_path)
                article_title = _short_caption(
                    article.get("title", ""),
                    fallback_body=article.get("body", ""),
                )
                caption = (
                    f"{article_title}  ·  Part {idx + 1}/{n_chunks}"
                    if article_title else f"Part {idx + 1}/{n_chunks}"
                )
                with open(chunk_path, "rb") as f:
                    await bot.send_voice(
                        chat_id=chat_id,
                        voice=f,
                        duration=int(dur) if dur > 0 else None,
                        caption=caption,
                    )
                sent += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Error sending split-voice part: {e}")
    finally:
        for f in os.listdir(chunk_dir):
            try:
                os.remove(os.path.join(chunk_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(chunk_dir)
        except OSError:
            pass

    return sent


async def _send_chapter_list(bot: Bot, chat_id: int, chapters: list, lang: str):
    """Send a text message listing chapter timestamps + truncated titles
    so the user can scrub the preceding voice message to a specific article.
    Format per line: "M:SS — Title". Capped at Telegram's 4096-char message
    limit; very long batches are truncated with a hint.
    """
    if not chapters:
        return

    header = t("chapters_header", lang)
    lines = [header]
    for article, start_seconds in chapters:
        title = _short_caption(
            article.get("title", ""),
            fallback_body=article.get("body", ""),
        ) or article.get("id", "")
        ts = format_timestamp(start_seconds)
        lines.append(f"{ts} — {title}")

    text = "\n".join(lines)
    # Telegram message limit is 4096 chars. Trim with an ellipsis if longer.
    if len(text) > 4000:
        text = text[:3990].rstrip() + "\n…"
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Chapter list send error: {e}")


async def _send_audio_fallback(bot: Bot, chat_id: int, results: list):
    """Fallback when ffmpeg isn't available: send each article's MP3 as a
    Telegram music track (sendAudio). No mobile speed control, but better
    than silent zero-audio. Mirrors the previous send_audio_files behavior.
    """
    sent = 0
    for article, audio_path in results:
        if not audio_path or not os.path.exists(audio_path):
            continue

        title = article.get("title", "News")
        if not title:
            title = (article.get("body", "") or "")[:60] + "..."

        try:
            with open(audio_path, "rb") as audio_file:
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=title[:64],
                    performer="Spot News",
                )
            sent += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[voice fallback] error sending audio: {e}")

    return sent


def _split_message(text, limit):
    """Split a message into chunks that fit within Telegram's char limit.

    Splits at paragraph boundaries (double newlines) when possible,
    falling back to single newlines, then hard splits.
    """
    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        # Try to split at a paragraph boundary
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at == -1 or split_at < limit // 2:
            # Try single newline
            split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1 or split_at < limit // 2:
            # Hard split at limit
            split_at = limit

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    return chunks


def _escape_html(text):
    """Escape HTML special chars for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
