"""Per-user article favorites — tapping the inline Save button, or
using /save <post_id>, writes a row here.

Stores a compact snapshot (title + body) so favorites survive even if
spot.uz rewrites or removes the source page.
"""

from __future__ import annotations

from typing import Any

from spot_bot.storage import db

# Telegram captions / body previews we show in listings get truncated to this.
_PREVIEW_LEN = 300


async def add(user_id: int, post_id: str, title: str, body: str) -> None:
    await db.execute(
        """
        INSERT INTO favorites(user_id, post_id, title, body)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, post_id) DO UPDATE SET
            title = excluded.title,
            body = excluded.body,
            saved_at = CURRENT_TIMESTAMP
        """,
        (user_id, post_id, title or "", body or ""),
    )


async def remove(user_id: int, post_id: str) -> bool:
    conn = await db.get_conn()
    async with conn.execute(
        "DELETE FROM favorites WHERE user_id = ? AND post_id = ?",
        (user_id, post_id),
    ) as cur:
        deleted = cur.rowcount > 0
    await conn.commit()
    return deleted


async def exists(user_id: int, post_id: str) -> bool:
    row = await db.fetchone(
        "SELECT 1 FROM favorites WHERE user_id = ? AND post_id = ?",
        (user_id, post_id),
    )
    return row is not None


async def list_for(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    rows = await db.fetchall(
        """
        SELECT post_id, title, body, saved_at
          FROM favorites
         WHERE user_id = ?
         ORDER BY saved_at DESC
         LIMIT ?
        """,
        (user_id, limit),
    )
    return [
        {
            "post_id": r["post_id"],
            "title": r["title"] or "",
            "preview": (r["body"] or "")[:_PREVIEW_LEN],
            "saved_at": r["saved_at"],
        }
        for r in rows
    ]
