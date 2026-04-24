"""Article summarization via the Anthropic Claude API.

Summaries are cached per (url, lang) in the article_cache table to
avoid spending tokens on repeats. Uses Claude Haiku for cost/latency
and prompt-caching on the system prompt across a batch.

Silently no-ops if ANTHROPIC_API_KEY isn't set or the SDK isn't
installed. Callers check `is_available()` before wiring summaries
into the pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from spot_bot.storage import db

logger = logging.getLogger(__name__)

# The Anthropic model ID to use. Defaults to Claude Haiku 4.5 (fast +
# cheap, good enough for 2-sentence summaries). Override via the
# ANTHROPIC_MODEL env var if Anthropic retires or renames it, or if
# you want to upgrade to a larger model for a specific deployment.
_DEFAULT_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 180  # plenty for 2 sentences
_CONCURRENCY = 4


def _model() -> str:
    return os.environ.get("ANTHROPIC_MODEL") or _DEFAULT_MODEL

# System prompt. Marked as cache-eligible via `cache_control` so the
# same batch of summary requests shares a single prompt read.
_SYSTEM_PROMPT = (
    "You summarize news articles in exactly two sentences. "
    "Write in the target language. Lead with the what happened, "
    "then the why or impact. No preamble, no bullets, no quoted phrases — "
    "just two sentences, each under 30 words. "
    "If the article is too short or not substantive, write a single sentence."
)


def is_available() -> bool:
    """True if summarization is possible (key present + SDK importable)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


async def _ensure_cache_table() -> None:
    """Lazily add the summary_cache table. Keeps the core migration
    minimal — summaries are a fringe feature and shouldn't block startup."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS summary_cache (
            post_id   TEXT NOT NULL,
            lang      TEXT NOT NULL,
            summary   TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (post_id, lang)
        )
        """,
    )


async def _lookup(post_id: str, lang: str) -> str | None:
    row = await db.fetchone(
        "SELECT summary FROM summary_cache WHERE post_id = ? AND lang = ?",
        (post_id, lang),
    )
    return row["summary"] if row else None


async def _store(post_id: str, lang: str, summary: str) -> None:
    await db.execute(
        """
        INSERT INTO summary_cache(post_id, lang, summary)
        VALUES (?, ?, ?)
        ON CONFLICT(post_id, lang) DO UPDATE SET
            summary = excluded.summary,
            created_at = CURRENT_TIMESTAMP
        """,
        (post_id, lang, summary),
    )


def _lang_name(lang: str) -> str:
    return {"en": "English", "ru": "Russian", "uz": "Uzbek"}.get(lang, "English")


async def _summarize_one(client: Any, article: dict[str, Any], lang: str) -> str:
    """Run a single Claude call. Caller handles caching + errors."""
    title = article.get("title", "").strip()
    body = article.get("body", "").strip()
    # Truncate body — Haiku handles 200k context but we don't need it, and
    # shorter prompts are faster.
    body = body[:6000]
    content = f"Language: {_lang_name(lang)}\n\nTitle: {title}\n\nBody:\n{body}"

    # Run the blocking SDK call in a worker thread so we don't stall
    # the event loop.
    def _call() -> Any:
        return client.messages.create(
            model=_model(),
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": content}],
        )

    resp = await asyncio.to_thread(_call)
    # Response blocks are TextBlock-like; concatenate their .text.
    parts = []
    for block in resp.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


async def summarize_batch(
    articles: list[dict[str, Any]],
    lang: str = "en",
    progress_callback: Any = None,
) -> None:
    """Add a `summary` key to every article in `articles` (in place).

    Uses the summary cache to avoid re-spending tokens. Silently no-ops
    if the API isn't available. Articles whose summarization fails get
    no `summary` key (callers should handle absence).
    """
    if not is_available():
        logger.info("AI summaries unavailable (no ANTHROPIC_API_KEY or SDK); skipping")
        return
    if not articles:
        return

    import anthropic

    await _ensure_cache_table()

    client = anthropic.Anthropic()

    # Check cache first.
    needs_fetch = []
    for a in articles:
        post_id = a.get("id", "")
        if not post_id:
            continue
        cached = await _lookup(post_id, lang)
        if cached:
            a["summary"] = cached
        else:
            needs_fetch.append(a)

    if progress_callback:
        await progress_callback(
            f"Summarizing {len(needs_fetch)}/{len(articles)} articles "
            f"({len(articles) - len(needs_fetch)} cached)..."
        )

    sem = asyncio.Semaphore(_CONCURRENCY)
    done = 0
    lock = asyncio.Lock()

    async def _work(article: dict[str, Any]) -> None:
        nonlocal done
        async with sem:
            try:
                text = await _summarize_one(client, article, lang)
            except Exception as e:
                logger.warning(
                    "Summary failed for %s: %s",
                    article.get("id", "?"), e,
                )
                return
            article["summary"] = text
            pid = article.get("id", "")
            if pid:
                await _store(pid, lang, text)

        if progress_callback:
            async with lock:
                done += 1
                if done % 5 == 0 or done == len(needs_fetch):
                    await progress_callback(
                        f"Summarized {done}/{len(needs_fetch)}..."
                    )

    await asyncio.gather(*[_work(a) for a in needs_fetch])
