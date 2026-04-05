import asyncio
import os
import tempfile
from telegram import Bot
from telegram.constants import ParseMode
from spot_bot.config import TELEGRAM_MESSAGE_LIMIT


async def send_articles_as_text(bot: Bot, chat_id: int, articles: list):
    """Send cleaned articles as Telegram messages.

    Splits long articles at paragraph boundaries to stay within
    Telegram's 4096-char limit.
    """
    for i, article in enumerate(articles):
        title = article.get("title", "")
        body = article.get("body", "")
        date = article.get("date", "")

        # Format the message
        header = ""
        if title:
            header = f"<b>{_escape_html(title)}</b>\n"
        if date:
            header += f"<i>{date}</i>\n"
        if header:
            header += "\n"

        full_text = header + _escape_html(body)

        # Split and send
        chunks = _split_message(full_text, TELEGRAM_MESSAGE_LIMIT)
        for chunk in chunks:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
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

        if title:
            lines.append(title)
        if date:
            lines.append(f"Date: {date}")
        if title or date:
            lines.append("")
        if body:
            lines.append(body)
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


async def send_combined_audio(bot: Bot, chat_id: int, combined_path: str,
                              article_count: int):
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
        print(f"Error sending combined audio: {e}")
        return False


async def send_audio_files(bot: Bot, chat_id: int, results: list):
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
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=title[:64],
                    performer="Spot News",
                )
            sent += 1
            await asyncio.sleep(0.5)  # Rate limiting for audio
        except Exception as e:
            print(f"Error sending audio: {e}")

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
