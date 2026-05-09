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

    def __init__(self, group_should_fail=False, url_should_fail=False):
        self.group_should_fail = group_should_fail
        self.url_should_fail = url_should_fail
        self.media_group_calls = 0
        self.photo_url_calls = 0
        self.photo_file_calls = 0

    async def send_media_group(self, chat_id, media):
        self.media_group_calls += 1
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


# ---------- Group fails → per-photo URL works ----------

@pytest.mark.asyncio
async def test_album_group_fails_per_photo_url_succeeds():
    bot = _FakeBot(group_should_fail=True, url_should_fail=False)
    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(3)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 3
    assert bot.media_group_calls == 1
    assert bot.photo_url_calls == 3   # one per image
    assert bot.photo_file_calls == 0  # never needed download


# ---------- Group fails AND per-URL fails → download fallback ----------

@pytest.mark.asyncio
async def test_album_group_and_url_fail_download_fallback(monkeypatch):
    """Both group send and per-URL send fail → download bytes and upload.
    This is the path that rescues telesco.pe expiry / webp rejection."""
    bot = _FakeBot(group_should_fail=True, url_should_fail=True)

    async def fake_download(url):
        return b"\xff\xd8\xff\xe0fake_jpeg_bytes"  # JPEG magic + payload

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": f"https://example.com/{i}.jpg"} for i in range(3)]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 3
    assert bot.photo_url_calls == 3   # tried URL each time
    assert bot.photo_file_calls == 3  # then downloaded each


@pytest.mark.asyncio
async def test_album_group_and_url_fail_download_also_fails(monkeypatch):
    """All three send paths fail → image is dropped, but no exception."""
    bot = _FakeBot(group_should_fail=True, url_should_fail=True)

    async def fake_download(url):
        return None  # download itself failed

    monkeypatch.setattr(ts, "_download_image", fake_download)

    images = [{"url": "https://example.com/dead.jpg"}]
    sent = await ts._send_image_album(bot, 1, images)
    assert sent == 0


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
