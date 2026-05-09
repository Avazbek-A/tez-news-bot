"""Two-to-three sentence article summaries via Groq's free tier.

Groq serves open-source Llama models at very generous free quotas
(14,400 requests/day on llama-3.1-8b-instant as of 2026), with
multilingual support good enough for Russian + Uzbek + English.

Falls back gracefully (returns None) when:
- GROQ_API_KEY env var is missing
- the `groq` SDK isn't installed
- the API call fails for any reason

Pipeline integration: spot_bot/pipeline.py only calls `summarize` when
the user has enabled summaries via /summarize on. Cache lookups go
through spot_bot.history_db so re-scraping a known article skips the
LLM round trip.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


# Cap input body length to keep token costs predictable. Groq's free
# tier has a per-minute token budget; long articles get summarized
# from their first 4k chars (which is the lede + first few sections,
# usually enough to capture the main facts).
_MAX_INPUT_CHARS = 4000

# 8b-instant is fast and free at the highest daily quota. Quality
# is fine for news summaries; we don't need a frontier model here.
_DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

_LANG_INSTRUCTION = {
    "en": "in English",
    "ru": "in Russian (по-русски)",
    "uz": "in Uzbek (o'zbek tilida)",
}


def _build_prompt(title: str, body: str, lang: str) -> str:
    lang_inst = _LANG_INSTRUCTION.get(lang, "in the same language as the article")
    return (
        f"Summarize this news article in 2-3 short sentences {lang_inst}. "
        f"Focus on the main facts. Do NOT add any preamble like 'Here is a "
        f"summary' — output the summary directly.\n\n"
        f"Title: {title}\n\n"
        f"Article:\n{body}\n\n"
        f"Summary:"
    )


async def summarize(article: dict, lang: str = "en") -> str | None:
    """Return a 2-3 sentence summary of `article`, or None on any failure.

    Goes through the shared Groq helper (spot_bot.groq_client) so
    rate-limit retries are handled centrally. Summary-specific
    post-processing (stripping LLM preamble like 'Here is a summary:')
    stays here.
    """
    body = (article.get("body") or "").strip()
    if not body:
        return None
    body = body[:_MAX_INPUT_CHARS]
    title = (article.get("title") or "").strip()

    prompt = _build_prompt(title, body, lang)

    from spot_bot.groq_client import chat_completion
    text = await chat_completion(
        prompt,
        max_tokens=220,
        temperature=0.3,
        model=_DEFAULT_MODEL,
        log_tag="summary",
    )
    if not text:
        return None
    # Strip common preamble patterns the model sometimes adds anyway.
    for prefix in (
        "Here is a summary:", "Summary:", "Краткое содержание:",
        "Резюме:", "Vot xulosa:",
    ):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].lstrip()
    return text or None
