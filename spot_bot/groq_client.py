"""Shared Groq chat-completion helper with rate-limit-aware retry.

Both spot_bot/translation.py and spot_bot/summary.py go through this
module so the 30-RPM / 14,400-RPD free-tier limits are handled the
same way: on HTTP 429 we read the Retry-After header, sleep that long
(capped to a safety ceiling), and retry up to _MAX_RETRIES times. On
any other failure we fall back to None and let the caller deliver the
article without the LLM-generated content.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# Retry configuration. Values chosen so /scrape 200 with translate=de
# can finish on the free tier without losing articles to 429s.
_MAX_RETRIES = 3
_DEFAULT_BACKOFF_SECONDS = 5.0
_MAX_SLEEP_SECONDS = 60.0
_MIN_SLEEP_SECONDS = 1.0

# Default model. Callers can override via the `model` arg.
_DEFAULT_MODEL_ENV = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")


async def chat_completion(prompt: str, *, max_tokens: int,
                          temperature: float = 0.3,
                          model: Optional[str] = None,
                          log_tag: str = "groq") -> Optional[str]:
    """Issue one chat completion via Groq's API. Retries on 429s.

    Args:
        prompt: User prompt content.
        max_tokens: Cap on output tokens.
        temperature: Sampling temperature.
        model: Override Groq model (default from GROQ_MODEL env / 8B).
        log_tag: Used in log lines, e.g. "translate" or "summary".

    Returns:
        Stripped response text on success, or None on:
          - missing GROQ_API_KEY
          - groq SDK not installed
          - rate-limit retries exhausted
          - any other API error
    """
    api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key:
        return None

    try:
        from groq import AsyncGroq
        # RateLimitError / APIError are exposed at module top-level in
        # current groq SDK versions. Older versions had them under
        # groq.errors; we try both.
        try:
            from groq import RateLimitError, APIError  # type: ignore
        except ImportError:  # pragma: no cover
            from groq import APIError  # type: ignore
            RateLimitError = APIError  # fallback so isinstance still narrows
    except ImportError:
        logger.warning("[%s] groq SDK not installed", log_tag)
        return None

    client = AsyncGroq(api_key=api_key)
    use_model = model or _DEFAULT_MODEL_ENV

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.chat.completions.create(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or None
        except RateLimitError as e:
            if attempt >= _MAX_RETRIES:
                logger.warning(
                    "[%s] rate limit exhausted after %d attempts",
                    log_tag, _MAX_RETRIES + 1,
                )
                return None
            sleep_s = _retry_after_from(e)
            sleep_s = min(_MAX_SLEEP_SECONDS, max(_MIN_SLEEP_SECONDS, sleep_s))
            logger.info(
                "[%s] rate-limited (attempt %d/%d), sleeping %.1fs",
                log_tag, attempt + 1, _MAX_RETRIES + 1, sleep_s,
            )
            await asyncio.sleep(sleep_s)
        except APIError as e:
            # Server-side / network errors. One short retry, then give up.
            if attempt >= 1:
                logger.warning("[%s] API error after retry: %s", log_tag, e)
                return None
            logger.info("[%s] API error, retrying once: %s", log_tag, e)
            await asyncio.sleep(2.0)
        except Exception as e:
            logger.warning("[%s] unexpected error: %s", log_tag, e)
            return None

    return None


def _retry_after_from(exc) -> float:
    """Extract Retry-After header (seconds) from a Groq rate-limit error.
    Falls back to _DEFAULT_BACKOFF_SECONDS if the header isn't present
    or isn't a number we can parse."""
    try:
        resp = getattr(exc, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None) or {}
            # httpx headers are case-insensitive but be defensive
            value = (
                headers.get("retry-after")
                if hasattr(headers, "get") else None
            ) or (
                headers.get("Retry-After")
                if hasattr(headers, "get") else None
            )
            if value:
                return float(value)
    except (ValueError, TypeError, AttributeError):
        pass
    return _DEFAULT_BACKOFF_SECONDS
