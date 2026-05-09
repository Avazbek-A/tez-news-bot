"""Tests for image-album delivery with URL → download fallback.

Telegram's send_media_group / send_photo with a URL fails when the URL
returns 404 (telesco.pe URLs expire) or when Telegram's URL fetcher
rejects the format (.webp via URL is unreliable). The sender must fall
back to downloading the bytes locally and uploading as InputFile so a
single bad URL doesn't drop the entire album.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import spot_bot.delivery.telegram_sender as ts


class _FakeBot:
    """Minimal Bot with the methods _send_image_album touches."""

    def __init__(self, group_should_fail=False, url_should_fail=False,
                 file_group_should_fail=False):
        self.group_should_fail = group_should_fail
        self.url_should_fail = url_should_fail
        self.file_group_should_fail = file_group_should_fail
        self.media_group_calls = 0          # all media_group calls
        self.media_group_url_calls = 0      # group send with URL items
        self.media_group_file_calls = 0     # group send with InputFile items
        self.photo_url_calls = 0
        self.photo_file_calls = 0

    async def send_media_group(self, chat_id, media):
        self.media_group_calls += 1
        # Detect whether this group is URL-based or file-based by
        # inspecting the first item's media field type.
        is_file = bool(media) and not isinstance(media[0].media, str)
        if is_file:
            self.media_group_file_calls += 1
            if self.file_group_should_fail:
                raise Exception("File group failed too")
        else:
            self.media_group_url_calls += 1
            if self.group_should_fail:
                raise Exception("URL fetch failed: 404")
        return True

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        # Distinguish URL strings from in-memory file uploads
        if isinstance(photo, str):
            self.photo_url_calls += 1
            if self.url_should_fail:
                raise Exception("PHOTO_INVALID_DIMENSIONS or URL fetch failed")
            return True
        else:
            self.photo_file_calls += 1
            return True


# ---------- Group success ----------

@pytest.mark.asyncio
async def test_album_group_success_no_fallback():
    bot = _FakeBot()
    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(5)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 5
    assert bot.media_group_calls == 1
    assert bot.photo_url_calls == 0
    assert bot.photo_file_calls == 0


# ---------- Group with URLs fails → download all → resend as ONE group ----------

@pytest.mark.asyncio
async def test_album_url_group_fails_resends_as_file_group(monkeypatch):
    """When URL-mode media_group fails, we must download every image and
    resend as a SINGLE InputFile media_group — preserving the tight
    gallery layout. Critical regression test for the gallery-format fix."""
    bot = _FakeBot(group_should_fail=True)

    async def fake_download(url):
        return b"\xff\xd8\xff\xe0fake_jpeg"

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(5)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 5
    # Exactly two media_group calls: one URL attempt + one InputFile retry.
    # Crucially, there must be NO per-photo send_photo calls (those would
    # mean the gallery was scattered into individual messages).
    assert bot.media_group_url_calls == 1
    assert bot.media_group_file_calls == 1
    assert bot.photo_url_calls == 0
    assert bot.photo_file_calls == 0


@pytest.mark.asyncio
async def test_album_url_group_fails_partial_downloads(monkeypatch):
    """Some URLs download, others 404. The successful ones still ship
    as ONE media_group (with fewer items)."""
    bot = _FakeBot(group_should_fail=True)
    counter = {"n": 0}

    async def fake_download(url):
        counter["n"] += 1
        # Every other download fails
        return b"\xff\xd8\xff\xe0jpeg" if counter["n"] % 2 == 0 else None

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(4)]
    sent = await ts._send_image_album(bot, 1, images)
    # 2 succeeded downloads → still one tight media_group of 2
    assert sent == 2
    assert bot.media_group_file_calls == 1


@pytest.mark.asyncio
async def test_album_all_downloads_fail(monkeypatch):
    """Every download fails → no items to send → returns 0, no exception."""
    bot = _FakeBot(group_should_fail=True)

    async def fake_download(url):
        return None

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(3)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 0
    # We attempted the URL group; no file group attempted because no bytes.
    assert bot.media_group_url_calls == 1
    assert bot.media_group_file_calls == 0


@pytest.mark.asyncio
async def test_album_file_group_also_fails_per_photo_last_resort(monkeypatch):
    """If even the InputFile media_group fails, fall back to per-photo
    sends so at least the working ones land. Loses grid layout but
    better than 0."""
    bot = _FakeBot(group_should_fail=True, file_group_should_fail=True)

    async def fake_download(url):
        return b"\xff\xd8\xff\xe0jpeg"

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(3)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 3
    assert bot.photo_file_calls == 3


# ---------- Single-image path uses fallback too ----------

@pytest.mark.asyncio
async def test_single_image_uses_download_fallback(monkeypatch):
    """The single-image fast path (avoids media_group entirely) must
    also have the download fallback."""
    bot = _FakeBot(url_should_fail=True)

    async def fake_download(url):
        return b"\xff\xd8\xff\xe0fake_jpeg"

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": "https://example.com/single.webp", "alt": "x"}]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 1
    assert bot.photo_url_calls == 1
    assert bot.photo_file_calls == 1


# ---------- Empty/invalid input ----------

@pytest.mark.asyncio
async def test_album_empty_input_returns_zero():
    bot = _FakeBot()
    assert await ts._send_image_album(bot, 1, []) == 0
    assert await ts._send_image_album(bot, 1, [{"url": ""}]) == 0
    assert await ts._send_image_album(bot, 1, [{}]) == 0
    assert bot.media_group_calls == 0


# ---------- Chunking past 10-item cap ----------

@pytest.mark.asyncio
async def test_album_chunks_over_ten_items():
    bot = _FakeBot()
    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(23)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 23
    # 23 items → 3 chunks (10 + 10 + 3)
    assert bot.media_group_calls == 3


# ---------- _download_image: 404 returns None ----------

@pytest.mark.asyncio
async def test_download_image_returns_none_on_404(monkeypatch):
    """Helper smoke: 404 response → None, no exception."""

    class _FakeResp:
        status_code = 404
        content = b""

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return _FakeResp()

    def fake_async_client(*a, **kw):
        return _FakeClient()

    monkeypatch.setattr(ts.httpx, "AsyncClient", fake_async_client)
    result = await ts._download_image("https://example.com/dead.jpg")
    assert result is None


@pytest.mark.asyncio
async def test_download_image_returns_bytes_on_200(monkeypatch):
    class _FakeResp:
        status_code = 200
        content = b"\xff\xd8\xff\xe0image_bytes"

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return _FakeResp()

    monkeypatch.setattr(ts.httpx, "AsyncClient", lambda *a, **kw: _FakeClient())
    result = await ts._download_image("https://example.com/ok.jpg")
    assert result == b"\xff\xd8\xff\xe0image_bytes"
