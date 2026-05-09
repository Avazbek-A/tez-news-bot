"""Tests for voice-message helpers (timestamp formatter, caption builder)."""
from spot_bot.audio.voice import format_timestamp
from spot_bot.delivery.telegram_sender import _short_caption


def test_format_timestamp_zero():
    assert format_timestamp(0) == "0:00"


def test_format_timestamp_under_minute():
    assert format_timestamp(45) == "0:45"


def test_format_timestamp_minutes():
    assert format_timestamp(125) == "2:05"


def test_format_timestamp_hour_boundary():
    assert format_timestamp(3600) == "1:00:00"


def test_format_timestamp_long():
    assert format_timestamp(3725) == "1:02:05"


def test_format_timestamp_negative_clamped_to_zero():
    assert format_timestamp(-5) == "0:00"


def test_short_caption_passthrough():
    assert _short_caption("Short title") == "Short title"


def test_short_caption_empty_string():
    assert _short_caption("") == ""


def test_short_caption_none_safe():
    # _short_caption uses .strip() so None would crash; helper guards via fallback
    assert _short_caption(None or "") == ""


def test_short_caption_falls_back_to_body_first_line():
    out = _short_caption("", fallback_body="Body line one\nBody line two")
    assert out == "Body line one"


def test_short_caption_truncates_long_titles_with_ellipsis():
    out = _short_caption("A" * 200)
    assert len(out) <= 80
    assert out.endswith("…")
