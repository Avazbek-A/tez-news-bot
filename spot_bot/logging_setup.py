"""Centralized logging configuration.

Default: human-readable single-line format with timestamps.
When LOG_FORMAT=json: structured JSON, one record per line.

Call configure_logging() once at process startup BEFORE any other
spot_bot imports run their own logger.basicConfig.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time


_HUMAN_FMT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

# Telegram bot tokens look like "123456789:AA...". Redact them anywhere
# (e.g. if a bot-API URL is ever logged) even if the exact value wasn't
# in the env at startup.
# No leading \b: the token usually appears as ".../bot<digits>:<token>",
# and there is no word boundary between "bot" and the digits.
_TG_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")
_REDACTED = "***REDACTED***"


class RedactingFilter(logging.Filter):
    """Scrub secret values from log records before they're emitted.

    Redacts the exact secret strings present in the environment
    (BOT_TOKEN, GROQ_API_KEY, SENTRY_DSN) plus anything matching the
    Telegram-token shape. Pre-renders the message so both the human and
    JSON formatters see the redacted text.
    """

    def __init__(self, secrets):
        super().__init__()
        # Only redact non-trivial values to avoid mangling normal text.
        self._secrets = sorted(
            {s for s in secrets if s and len(s) >= 8}, key=len, reverse=True
        )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        red = msg
        for secret in self._secrets:
            if secret in red:
                red = red.replace(secret, _REDACTED)
        red = _TG_TOKEN_RE.sub(_REDACTED, red)
        if red != msg:
            record.msg = red
            record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter — no external deps."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("chat_id", "post_id", "source_id", "voice_engine"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt_choice = os.environ.get("LOG_FORMAT", "human").lower()

    handler = logging.StreamHandler(stream=sys.stdout)
    if fmt_choice == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_HUMAN_FMT))

    # Never let secrets reach the logs.
    handler.addFilter(RedactingFilter([
        os.environ.get("BOT_TOKEN", ""),
        os.environ.get("GROQ_API_KEY", ""),
        os.environ.get("SENTRY_DSN", ""),
    ]))

    root = logging.getLogger()
    # Wipe any handlers attached by other libraries before this point so we
    # don't double-print every record.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "telegram.ext.Application"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
