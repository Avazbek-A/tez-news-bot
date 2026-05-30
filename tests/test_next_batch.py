"""Tests for the one-tap 'next batch' button."""
from __future__ import annotations

import asyncio
import types

import pytest

from spot_bot.commands import common
from spot_bot.commands import scrape


# ---------- flag encode/decode ----------

def test_flags_roundtrip_text_default():
    f = common.encode_next_batch_flags(
        include_audio=False, combined_audio=False, include_images=False,
        send_as_file=True, include_seen=False,
    )
    assert f == "t"
    opts = common.decode_next_batch_flags(f)
    assert opts == {
        "include_audio": False, "combined_audio": False,
        "include_images": False, "send_as_file": True, "include_seen": False,
    }


def test_flags_roundtrip_combined_audio_images():
    f = common.encode_next_batch_flags(
        include_audio=True, combined_audio=True, include_images=True,
        send_as_file=True, include_seen=False,
    )
    opts = common.decode_next_batch_flags(f)
    assert opts["include_audio"] is True
    assert opts["combined_audio"] is True
    assert opts["include_images"] is True
    assert opts["send_as_file"] is True


def test_flags_roundtrip_inline_audio_seen():
    f = common.encode_next_batch_flags(
        include_audio=True, combined_audio=False, include_images=False,
        send_as_file=False, include_seen=True,
    )
    opts = common.decode_next_batch_flags(f)
    assert opts["include_audio"] is True
    assert opts["combined_audio"] is False
    assert opts["send_as_file"] is False   # 'i' present
    assert opts["include_seen"] is True


def test_keyboard_callback_data_format():
    kb = common.next_batch_keyboard(37750, 37701, 50, "ac", "en")
    btn = kb.inline_keyboard[0][0]
    assert btn.callback_data == "nb_37750_37701_ac"
    assert "50" in btn.text
    # callback_data must fit Telegram's 64-byte cap.
    assert len(btn.callback_data.encode()) <= 64


# ---------- callback handler ----------

class _FakeQuery:
    def __init__(self, data, chat_id=99):
        self.data = data
        self.message = types.SimpleNamespace(chat_id=chat_id)
        self.answered = False
        self.markup_cleared = False

    async def answer(self):
        self.answered = True

    async def edit_message_reply_markup(self, reply_markup=None):
        self.markup_cleared = reply_markup is None


class _FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append(text)
        return types.SimpleNamespace(message_id=1, chat_id=chat_id)


@pytest.fixture(autouse=True)
def _clean_jobs(monkeypatch):
    monkeypatch.setattr(common, "_running_jobs", {})
    # scrape.py imported _running_jobs by name; point it at the same dict.
    monkeypatch.setattr(scrape, "_running_jobs", common._running_jobs)
    # Stable settings lookups.
    monkeypatch.setattr(scrape, "get_setting", lambda k: None)
    monkeypatch.setattr(scrape, "_get_voice", lambda: "v")
    monkeypatch.setattr(scrape, "_get_speed", lambda: "+0%")
    monkeypatch.setattr(scrape, "_get_lang", lambda: "en")


@pytest.mark.asyncio
async def test_next_batch_handler_launches_correct_range(monkeypatch):
    captured = {}

    async def fake_run_job(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(scrape, "_run_job", fake_run_job)

    query = _FakeQuery("nb_37750_37701_am")  # audio + images
    update = types.SimpleNamespace(
        callback_query=query,
        effective_chat=types.SimpleNamespace(id=99),
    )
    context = types.SimpleNamespace(bot=_FakeBot())

    await scrape._handle_next_batch(update, context)
    await asyncio.sleep(0)  # let the created task run

    assert query.answered is True
    assert query.markup_cleared is True
    assert captured["use_post_ids"] is True
    assert captured["start_post_id"] == 37750
    assert captured["end_post_id"] == 37701
    assert captured["count"] == 50
    assert captured["include_audio"] is True
    assert captured["include_images"] is True
    assert captured["combined_audio"] is False
    assert captured["send_as_file"] is True


@pytest.mark.asyncio
async def test_next_batch_handler_blocks_when_job_running(monkeypatch):
    ran = {"called": False}

    async def fake_run_job(**kwargs):
        ran["called"] = True

    monkeypatch.setattr(scrape, "_run_job", fake_run_job)
    scrape._running_jobs[99] = {"task": None, "cancel_event": None}

    query = _FakeQuery("nb_100_51_t")
    update = types.SimpleNamespace(
        callback_query=query,
        effective_chat=types.SimpleNamespace(id=99),
    )
    bot = _FakeBot()
    context = types.SimpleNamespace(bot=bot)

    await scrape._handle_next_batch(update, context)
    await asyncio.sleep(0)

    assert ran["called"] is False  # didn't start a second job


@pytest.mark.asyncio
async def test_next_batch_handler_ignores_bad_payload(monkeypatch):
    ran = {"called": False}

    async def fake_run_job(**kwargs):
        ran["called"] = True

    monkeypatch.setattr(scrape, "_run_job", fake_run_job)

    query = _FakeQuery("nb_notanumber")
    update = types.SimpleNamespace(
        callback_query=query,
        effective_chat=types.SimpleNamespace(id=99),
    )
    context = types.SimpleNamespace(bot=_FakeBot())

    await scrape._handle_next_batch(update, context)
    await asyncio.sleep(0)
    assert ran["called"] is False
