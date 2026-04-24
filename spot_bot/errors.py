"""User-facing error types.

Internally we log the full traceback; externally we show a short, translated,
actionable message. Raw exception text shouldn't reach end users (leaks file
paths, stack details, and is usually English-only).
"""

from __future__ import annotations

import asyncio

from spot_bot.translations import t


class UserFacingError(Exception):
    """An error whose message is safe to show to users.

    Carries a translation key and optional format params. Callers can catch
    this at the top level and render `.user_message(lang)` without worrying
    about leaking internal details.
    """

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        super().__init__(key)

    def user_message(self, lang: str) -> str:
        return t(self.key, lang, **self.params)


def classify_exception(exc: BaseException) -> UserFacingError:
    """Map an arbitrary exception to a UserFacingError with a translated key.

    Conservative: if nothing matches, fall back to the generic "error" key
    without leaking the raw exception text.
    """
    if isinstance(exc, UserFacingError):
        return exc
    if isinstance(exc, asyncio.TimeoutError):
        return UserFacingError("error_timeout")
    name = type(exc).__name__
    # Known Playwright / network error classes by name (avoid importing
    # optional deps at module load time).
    if "Timeout" in name:
        return UserFacingError("error_timeout")
    if "Network" in name or "Connection" in name or "DNS" in name:
        return UserFacingError("error_network")
    return UserFacingError("error_generic")
