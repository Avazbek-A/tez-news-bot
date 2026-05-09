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
import sys
import time


_HUMAN_FMT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


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
