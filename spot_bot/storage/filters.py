"""Per-user keyword filters (include/exclude) applied after cleaning.

Include mode: article must contain at least one include keyword (any-match).
Exclude mode: article is dropped if it contains any exclude keyword.

Both modes compose: if any include keywords exist, include-match is
required AND no exclude keyword may match.

Keywords are matched case-insensitively against title + body concatenated.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from spot_bot.storage import db

Article = dict[str, Any]

logger = logging.getLogger(__name__)

MODE_INCLUDE = "include"
MODE_EXCLUDE = "exclude"
_VALID_MODES = {MODE_INCLUDE, MODE_EXCLUDE}


async def add(user_id: int, keyword: str, mode: str = MODE_INCLUDE) -> None:
    if mode not in _VALID_MODES:
        raise ValueError(f"Invalid mode: {mode}")
    keyword = keyword.strip().lower()
    if not keyword:
        raise ValueError("Empty keyword")
    await db.execute(
        "INSERT OR IGNORE INTO keyword_filters(user_id, keyword, mode) "
        "VALUES (?, ?, ?)",
        (user_id, keyword, mode),
    )


async def remove(user_id: int, keyword: str, mode: str | None = None) -> int:
    """Remove a single filter. If `mode` is None, removes both include and
    exclude variants. Returns number of rows deleted."""
    keyword = keyword.strip().lower()
    conn = await db.get_conn()
    if mode is None:
        async with conn.execute(
            "DELETE FROM keyword_filters WHERE user_id = ? AND keyword = ?",
            (user_id, keyword),
        ) as cur:
            deleted = cur.rowcount
    else:
        async with conn.execute(
            "DELETE FROM keyword_filters WHERE user_id = ? AND keyword = ? AND mode = ?",
            (user_id, keyword, mode),
        ) as cur:
            deleted = cur.rowcount
    await conn.commit()
    return deleted


async def clear(user_id: int) -> int:
    conn = await db.get_conn()
    async with conn.execute(
        "DELETE FROM keyword_filters WHERE user_id = ?", (user_id,),
    ) as cur:
        deleted = cur.rowcount
    await conn.commit()
    return deleted


async def list_for(user_id: int) -> list[dict[str, str]]:
    rows = await db.fetchall(
        "SELECT keyword, mode FROM keyword_filters WHERE user_id = ? "
        "ORDER BY mode, keyword",
        (user_id,),
    )
    return [{"keyword": r["keyword"], "mode": r["mode"]} for r in rows]


async def get_sets(user_id: int) -> tuple[set[str], set[str]]:
    """Return (include_set, exclude_set) of lowercased keywords."""
    rows = await list_for(user_id)
    include = {r["keyword"] for r in rows if r["mode"] == MODE_INCLUDE}
    exclude = {r["keyword"] for r in rows if r["mode"] == MODE_EXCLUDE}
    return include, exclude


def _haystack(article: Article) -> str:
    parts = [article.get("title", ""), article.get("body", "")]
    return " ".join(parts).lower()


def apply_filters(
    articles: Iterable[Article],
    include: set[str],
    exclude: set[str],
) -> tuple[list[Article], list[Article]]:
    """Return (kept, dropped) articles after applying the filter sets.

    Pure function — no DB access. Tests can exercise it directly.
    """
    kept: list[Article] = []
    dropped: list[Article] = []
    for article in articles:
        text = _haystack(article)
        if include and not any(k in text for k in include):
            dropped.append(article)
            continue
        if exclude and any(k in text for k in exclude):
            dropped.append(article)
            continue
        kept.append(article)
    return kept, dropped
