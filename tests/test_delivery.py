"""Tests for delivery/telegram_sender.

Focus: the ⭐ Save button is actually attached to delivered articles
(regression test — this feature was documented but not wired for a bit),
and only to the last chunk when an article spans multiple messages.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from spot_bot.delivery.telegram_sender import (
    _split_message,
    save_button,
    send_articles_as_text,
)

# ---------------------------------------------------------------------------


def test_save_button_label_toggle():
    not_saved = save_button("spotuz/1", saved=False)
    saved = save_button("spotuz/1", saved=True)
    # Check button labels differ
    assert "⭐" in str(not_saved.inline_keyboard[0][0].text)
    assert "✅" in str(saved.inline_keyboard[0][0].text)
    # Callback data is the same, only label flips
    assert not_saved.inline_keyboard[0][0].callback_data == "fav:spotuz/1"
    assert saved.inline_keyboard[0][0].callback_data == "fav:spotuz/1"


def test_split_message_short_stays_one_chunk():
    assert _split_message("hello world", 4096) == ["hello world"]


def test_split_message_long_splits_at_paragraph():
    text = "para 1\n\npara 2\n\npara 3"
    chunks = _split_message(text, 10)
    assert len(chunks) >= 2
    joined = "".join(chunks).replace("\n", "")
    assert "para1" in joined.replace(" ", "") or "para 1" in joined or "para 2" in joined


def _make_mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=MagicMock())
    return bot


async def test_save_button_attached_to_short_article():
    bot = _make_mock_bot()
    articles = [{
        "id": "spotuz/34950",
        "title": "Test",
        "body": "Body text.",
        "date": "2026-04-24",
    }]

    await send_articles_as_text(bot, chat_id=42, articles=articles)

    assert bot.send_message.await_count == 1
    call = bot.send_message.await_args_list[0]
    markup = call.kwargs.get("reply_markup")
    assert markup is not None
    assert markup.inline_keyboard[0][0].callback_data == "fav:spotuz/34950"


async def test_save_button_only_on_last_chunk_of_split_article():
    bot = _make_mock_bot()
    # Large body guaranteed to exceed Telegram limit → multiple chunks
    huge_body = ("Paragraph text.\n\n" * 400)
    articles = [{
        "id": "spotuz/100",
        "title": "Big",
        "body": huge_body,
        "date": "2026-04-24",
    }]

    await send_articles_as_text(bot, chat_id=42, articles=articles)

    # Must have split into multiple chunks
    assert bot.send_message.await_count >= 2

    calls = bot.send_message.await_args_list
    # Every non-final chunk: no reply_markup
    for call in calls[:-1]:
        assert call.kwargs.get("reply_markup") is None, (
            "intermediate chunks should not carry the save button"
        )
    # Last chunk: has the button
    last = calls[-1]
    markup = last.kwargs.get("reply_markup")
    assert markup is not None
    assert markup.inline_keyboard[0][0].callback_data == "fav:spotuz/100"


async def test_no_save_button_when_article_has_no_id():
    bot = _make_mock_bot()
    articles = [{"title": "t", "body": "b", "date": "d"}]  # no id

    await send_articles_as_text(bot, chat_id=42, articles=articles)

    assert bot.send_message.await_count == 1
    assert bot.send_message.await_args_list[0].kwargs.get("reply_markup") is None


async def test_summary_rendered_when_present():
    bot = _make_mock_bot()
    articles = [{
        "id": "spotuz/5",
        "title": "T",
        "body": "Body",
        "date": "2026-04-24",
        "summary": "This is the generated summary.",
    }]

    await send_articles_as_text(bot, chat_id=42, articles=articles)

    text: str = bot.send_message.await_args_list[0].kwargs["text"]
    assert "📝" in text
    assert "generated summary" in text
