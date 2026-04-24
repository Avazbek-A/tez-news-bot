"""Tests for error classification into user-safe messages."""

import asyncio

from spot_bot.errors import UserFacingError, classify_exception


def test_timeouterror_maps_to_timeout_key():
    err = classify_exception(asyncio.TimeoutError())
    assert err.key == "error_timeout"


def test_user_facing_passes_through():
    original = UserFacingError("error_network")
    classified = classify_exception(original)
    assert classified is original


def test_unknown_exception_becomes_generic():
    err = classify_exception(ValueError("some internal detail"))
    assert err.key == "error_generic"


def test_user_message_renders_in_multiple_languages():
    err = UserFacingError("error_timeout")
    en = err.user_message("en")
    ru = err.user_message("ru")
    assert en != ru
    assert "timed" in en.lower() or "time" in en.lower()


def test_network_name_detection():
    class ConnectionError_(Exception):
        pass

    err = classify_exception(ConnectionError_("dns failed"))
    assert err.key == "error_network"
