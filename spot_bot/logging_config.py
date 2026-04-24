"""Central logging configuration for the Spot bot.

Call `setup_logging()` once at application startup. Every module should
use `logger = logging.getLogger(__name__)` and log through it — no
more `print()` calls in library code.

Operation IDs: use `get_op_logger(op_id)` at the top of a scrape job
to get a LoggerAdapter that prepends the op_id to every message. This
lets you grep a single run out of a shared log file.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# ContextVars auto-propagate through async/await chains, so an op_id set in
# _run_job is visible to every log call made downstream (scrapers, fetchers,
# cleaners, senders) without threading op_id through every function signature.
_op_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "spot_op_id", default=None
)
_user_id_var: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "spot_user_id", default=None
)


def set_op_context(op_id: str | None, user_id: int | None = None) -> None:
    """Bind op_id (and optional user_id) to the current async context.
    All log calls in this context will carry them."""
    _op_id_var.set(op_id)
    if user_id is not None:
        _user_id_var.set(user_id)


class _ContextFilter(logging.Filter):
    """Inject op_id/user_id from contextvars into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "op_id") or record.op_id is None:
            record.op_id = _op_id_var.get()
        if not hasattr(record, "user_id") or record.user_id is None:
            record.user_id = _user_id_var.get()
        return True


_LOG_DIR = Path(os.environ.get("SPOT_LOG_DIR", "logs"))
_LOG_FILE = _LOG_DIR / "spot_bot.log"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

_configured = False


class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for machine-readable logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # LoggerAdapter drops its 'extra' dict onto the record as attributes.
        for key in ("op_id", "post_id", "user_id", "url"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    """Human-friendly formatter that surfaces op_id / post_id when set."""

    _BASE = "%(asctime)s %(levelname)-7s %(name)s"

    def format(self, record: logging.LogRecord) -> str:
        context_bits = []
        for key in ("op_id", "post_id", "user_id"):
            val = getattr(record, key, None)
            if val is not None:
                context_bits.append(f"{key}={val}")
        context = f" [{' '.join(context_bits)}]" if context_bits else ""
        record.__spot_context__ = context
        fmt = self._BASE + "%(__spot_context__)s: %(message)s"
        return logging.Formatter(fmt, datefmt="%H:%M:%S").format(record)


def setup_logging(level: str | None = None, log_format: str | None = None) -> None:
    """Configure root logger. Idempotent — safe to call repeatedly.

    Env vars:
        LOG_LEVEL: DEBUG | INFO | WARNING | ERROR (default INFO)
        LOG_FORMAT: text | json (default text)
        SPOT_LOG_DIR: directory for rotating file logs (default ./logs)
    """
    global _configured
    if _configured:
        return

    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    fmt_name = (log_format or os.environ.get("LOG_FORMAT", "text")).lower()
    formatter: logging.Formatter = (
        _JsonFormatter() if fmt_name == "json" else _TextFormatter()
    )

    root = logging.getLogger()
    root.setLevel(level_name)

    # Clear any default handlers (e.g., basicConfig called elsewhere).
    for h in list(root.handlers):
        root.removeHandler(h)

    context_filter = _ContextFilter()

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    stream.addFilter(context_filter)
    root.addHandler(stream)

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root.addHandler(file_handler)
    except OSError as e:
        # Don't crash if we can't write logs to disk — stream handler still works.
        root.warning("Could not set up file log at %s: %s", _LOG_FILE, e)

    # Silence noisy third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    _configured = True


def new_op_id() -> str:
    """Generate a short operation ID for correlating logs across a job."""
    return uuid.uuid4().hex[:8]


def get_op_logger(
    logger: logging.Logger, op_id: str, **extra: Any
) -> logging.LoggerAdapter[logging.Logger]:
    """Return a LoggerAdapter that attaches op_id (and optional user_id etc.)
    to every record emitted through it.

    Usage:
        logger = logging.getLogger(__name__)
        log = get_op_logger(logger, op_id, user_id=42)
        log.info("Scraping started")
    """
    context = {"op_id": op_id, **extra}
    return logging.LoggerAdapter(logger, context)
