from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import NetworkError, RetryAfter, TimedOut

from spot_bot.config import (
    DELIVERY_AUDIO_DELAY_S,
    DELIVERY_IMAGE_DELAY_S,
    DELIVERY_TEXT_DELAY_S,
    TELEGRAM_MESSAGE_LIMIT,
)

logger = logging.getLogger(__name__)

Article = dict[str, Any]
AudioResult = tuple[Article, str | None]
CoroFactory = Callable[[], Awaitable[Any]]


def save_button(post_id: str, saved: bool = False) -> InlineKeyboardMarkup:
    """Build the inline ⭐ Save / ✅ Saved keyboard for an article.

    `post_id` is the full Telegram post ID like "spotuz/34950". Callback
    data follows the `fav:<post_id>` convention — handlers/features
    `on_save_callback` matches the pattern `^fav:`.
    """
    label = "✅ Saved" if saved else "⭐ Save"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"fav:{post_id}")]]
    )


async def _send_with_retry(coro_factory: CoroFactory, max_attempts: int = 3) -> Any:
    """Run a Telegram send coroutine factory with RetryAfter + backoff.

    `coro_factory` must be a zero-arg callable returning a fresh coroutine
    (Telegram coroutines can't be re-awaited).

    Honors Telegram's RetryAfter (server-requested sleep) exactly, and adds
    short backoff for TimedOut / NetworkError. Other exceptions propagate.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return await coro_factory()
        except RetryAfter as e:
            # retry_after can be int|timedelta depending on the PTB version.
            ra: Any = e.retry_after
            seconds: float = (
                ra.total_seconds() if hasattr(ra, "total_seconds") else float(ra)
            )
            wait = seconds + 0.5
            logger.warning("Telegram rate limit: sleeping %.1fs", wait)
            await asyncio.sleep(wait)
        except (TimedOut, NetworkError) as e:
            if attempt >= max_attempts:
                raise
            wait = 1.5 * attempt
            logger.info(
                "Telegram send transient error (%s); retry %d/%d in %.1fs",
                e, attempt, max_attempts, wait,
            )
            await asyncio.sleep(wait)


async def send_articles_as_text(
    bot: Bot, chat_id: int, articles: list[Article],
) -> None:
    """Send cleaned articles as Telegram messages.

    Splits long articles at paragraph boundaries to stay within
    Telegram's 4096-char limit.
    """
    for article in articles:
        title = article.get("title", "")
        body = article.get("body", "")
        date = article.get("date", "")
        summary = article.get("summary", "")

        # Post ID: full form ("spotuz/34950") for callback data, short form
        # ("34950") for the human-visible footer.
        raw_id = article.get("id", "")
        post_id_short = ""
        if "/" in raw_id:
            post_id_short = raw_id.split("/")[-1]

        # Format the message
        header = ""
        if title:
            header = f"<b>{_escape_html(title)}</b>\n"
        if date:
            header += f"<i>{date}</i>\n"
        if header:
            header += "\n"

        summary_block = ""
        if summary:
            summary_block = f"<i>📝 {_escape_html(summary)}</i>\n\n"

        footer = ""
        if post_id_short:
            footer = f"\n\n<i>#{post_id_short}</i>"

        full_text = header + summary_block + _escape_html(body) + footer

        # Split into chunks; attach ⭐ Save keyboard to the last chunk only
        # (so it appears once per article, right below the final message).
        chunks = _split_message(full_text, TELEGRAM_MESSAGE_LIMIT)
        markup = save_button(raw_id) if raw_id else None
        last_idx = len(chunks) - 1
        for i, chunk in enumerate(chunks):
            reply_markup = markup if i == last_idx else None

            def _send(
                c: str = chunk,
                rm: InlineKeyboardMarkup | None = reply_markup,
            ) -> Any:
                return bot.send_message(
                    chat_id=chat_id,
                    text=c,
                    parse_mode=ParseMode.HTML,
                    reply_markup=rm,
                )

            await _send_with_retry(_send)
            await asyncio.sleep(DELIVERY_TEXT_DELAY_S)  # Rate limiting


async def send_articles_as_file(
    bot: Bot,
    chat_id: int,
    articles: list[Article],
    filename: str = "Spot_News.txt",
) -> None:
    """Send cleaned articles as a .txt document attachment.

    Builds a plain text file with all articles separated by dividers
    and sends it as a Telegram document.
    """
    lines: list[str] = []
    for article in articles:
        title = article.get("title", "")
        body = article.get("body", "")
        date = article.get("date", "")
        summary = article.get("summary", "")

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
        if summary:
            lines.append(f"📝 Summary: {summary}")
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


async def send_article_images(
    bot: Bot, chat_id: int, articles: list[Article],
) -> int:
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
                cap = caption[:200] if caption else None

                def _send_photo(u: str = url, cp: str | None = cap) -> Any:
                    return bot.send_photo(
                        chat_id=chat_id,
                        photo=u,
                        caption=cp,
                    )

                await _send_with_retry(_send_photo)
                sent += 1
                await asyncio.sleep(DELIVERY_IMAGE_DELAY_S)
            except Exception as e:
                logger.warning("Error sending image %s: %s", url, e)

    return sent


async def send_combined_audio(
    bot: Bot, chat_id: int, combined_path: str, article_count: int,
) -> bool:
    """Send a single combined MP3 file as a Telegram document.

    Uses send_document (not send_audio) since combined files can be large
    and don't map to a single track title.
    """
    filename = f"Spot_News_{article_count}_articles.mp3"
    file_size_mb = os.path.getsize(combined_path) / (1024 * 1024)

    if file_size_mb > 50:
        # Telegram bot document limit is 50MB
        return False

    try:
        with open(combined_path, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=filename,
            )
        return True
    except Exception as e:
        logger.error("Error sending combined audio: %s", e, exc_info=True)
        return False


async def send_audio_files(
    bot: Bot, chat_id: int, results: list[AudioResult],
) -> int:
    """Send generated audio files as Telegram audio messages.

    Args:
        bot: Telegram Bot instance.
        chat_id: Chat to send to.
        results: List of (article, audio_path) tuples from TTS generator.
    """
    sent = 0
    for article, audio_path in results:
        if not audio_path or not os.path.exists(audio_path):
            continue

        title = article.get("title", "News")
        if not title:
            title = article.get("body", "")[:60] + "..."

        try:
            with open(audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()

            def _send_audio(ab: bytes = audio_bytes, ttl: str = title) -> Any:
                return bot.send_audio(
                    chat_id=chat_id,
                    audio=ab,
                    title=ttl[:64],
                    performer="Spot News",
                )

            await _send_with_retry(_send_audio)
            sent += 1
            await asyncio.sleep(DELIVERY_AUDIO_DELAY_S)  # Rate limiting for audio
        except Exception as e:
            logger.warning("Error sending audio: %s", e)

    return sent


def _split_message(text: str, limit: int) -> list[str]:
    """Split a message into chunks that fit within Telegram's char limit.

    Splits at paragraph boundaries (double newlines) when possible,
    falling back to single newlines, then hard splits.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
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


def _escape_html(text: str) -> str:
    """Escape HTML special chars for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
