"""Tests for the secret-redacting log filter."""
from __future__ import annotations

import logging

from spot_bot.logging_setup import RedactingFilter, _REDACTED


def _record(msg, *args):
    return logging.LogRecord(
        name="t", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


def test_redacts_exact_secret():
    f = RedactingFilter(["super-secret-token-value"])
    rec = _record("connecting with %s", "super-secret-token-value")
    f.filter(rec)
    assert "super-secret-token-value" not in rec.getMessage()
    assert _REDACTED in rec.getMessage()


def test_redacts_telegram_token_shape():
    f = RedactingFilter([])  # no known secrets, rely on shape
    rec = _record("calling https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrSTUvwx/getMe")
    f.filter(rec)
    msg = rec.getMessage()
    assert "123456789:ABCdefGHIjklMNOpqrSTUvwx" not in msg
    assert _REDACTED in msg


def test_leaves_clean_messages_untouched():
    f = RedactingFilter(["a-real-secret-1234"])
    rec = _record("nothing sensitive here")
    f.filter(rec)
    assert rec.getMessage() == "nothing sensitive here"


def test_short_values_not_redacted():
    """Don't redact trivially short 'secrets' that would mangle normal text."""
    f = RedactingFilter(["abc"])  # too short (< 8 chars)
    rec = _record("the abc value is fine")
    f.filter(rec)
    assert rec.getMessage() == "the abc value is fine"


def test_filter_always_returns_true():
    """The filter must never drop a record."""
    f = RedactingFilter(["secret-value-here"])
    assert f.filter(_record("secret-value-here")) is True
