"""Article translation via Groq's free tier (Llama-3.1-8b-instant).

Translates article title + body to a target language so the user can
listen to e.g. spotuz Russian news in German or Turkish. Caches results
in history_db so re-scraping the same article skips the LLM call.

Falls back to None on any failure — pipeline keeps working with the
original text in that case.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# Same chunking budget as summary.py — keeps free-tier per-minute token
# usage predictable. Long articles will be split in two halves and the
# results joined; quality stays acceptable.
_MAX_INPUT_CHARS = 6000

# Default model (overridable via env var).
_DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")


_LANG_NAMES = {
    "en": "English",
    "ru": "Russian",
    "uz": "Uzbek",
    "de": "German",
    "tr": "Turkish",
}


def _build_prompt(text: str, target_lang: str) -> str:
    """Build the translation prompt. Crucially: NO chatty preamble, NO
    explanations — the model should output ONLY the translation."""
    target = _LANG_NAMES.get(target_lang, target_lang)
    return (
        f"Translate the following news text into {target}. "
        f"Preserve paragraph breaks. Do not add any preamble, explanation, "
        f"or quotation marks — output ONLY the {target} translation.\n\n"
        f"---\n{text}\n---"
    )


async def _call_groq(prompt: str, max_tokens: int) -> Optional[str]:
    """Translate a single prompt via the shared Groq helper. Retries on
    429s automatically. Translation-specific post-processing (stripping
    the model's occasional `---` / ```` echoes) stays here."""
    from spot_bot.groq_client import chat_completion
    text = await chat_completion(
        prompt,
        max_tokens=max_tokens,
        temperature=0.2,
        model=_DEFAULT_MODEL,
        log_tag="translate",
    )
    if not text:
        return None
    for delim in ("---", "```"):
        if text.startswith(delim):
            text = text[len(delim):].lstrip()
        if text.endswith(delim):
            text = text[:-len(delim)].rstrip()
    return text or None


async def translate_text(text: str, target_lang: str) -> Optional[str]:
    """Translate `text` into target_lang. Returns None on any failure."""
    if not text or not text.strip():
        return None
    if target_lang not in _LANG_NAMES:
        logger.warning("[translate] unknown target language: %s", target_lang)
        return None

    if len(text) <= _MAX_INPUT_CHARS:
        return await _call_groq(_build_prompt(text, target_lang), max_tokens=2400)

    # Long text — split in halves at paragraph boundaries.
    halves = _split_for_translation(text, _MAX_INPUT_CHARS)
    parts: list[str] = []
    for half in halves:
        result = await _call_groq(
            _build_prompt(half, target_lang), max_tokens=2400,
        )
        if not result:
            return None
        parts.append(result)
    return "\n\n".join(parts)


async def translate_article(article: dict, target_lang: str) -> Optional[dict]:
    """Translate an article's title + body. Returns a dict
    {"title": ..., "body": ...} or None on failure."""
    title = (article.get("title") or "").strip()
    body = (article.get("body") or "").strip()
    if not body:
        return None

    if title:
        translated_title = await translate_text(title, target_lang)
    else:
        translated_title = ""
    translated_body = await translate_text(body, target_lang)
    if translated_body is None:
        return None
    return {
        "title": translated_title or "",
        "body": translated_body,
    }


def _split_for_translation(text: str, limit: int) -> list[str]:
    """Split text into chunks ≤ `limit` chars at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        candidate = (buf + "\n\n" + p) if buf else p
        if len(candidate) <= limit:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks
