"""Persistent audit trail of scrape operations.

Ties together the op_id from logging_config with user-visible outcome
(ok / failed / cancelled, article count, error reason). Useful for
"why did last night's auto-scrape fail?" questions.
"""

from __future__ import annotations

import json
from typing import Any

from spot_bot.storage import db


async def start(
    op_id: str,
    user_id: int,
    command: str,
    args: dict[str, Any] | None = None,
) -> None:
    await db.execute(
        """
        INSERT INTO operation_log(op_id, user_id, command, args_json, status)
        VALUES (?, ?, ?, ?, 'running')
        """,
        (op_id, user_id, command, json.dumps(args or {}, ensure_ascii=False)),
    )


async def complete(op_id: str, article_count: int) -> None:
    await db.execute(
        """
        UPDATE operation_log
           SET status = 'ok',
               completed_at = CURRENT_TIMESTAMP,
               article_count = ?
         WHERE op_id = ?
        """,
        (article_count, op_id),
    )


async def fail(op_id: str, error: str) -> None:
    await db.execute(
        """
        UPDATE operation_log
           SET status = 'failed',
               completed_at = CURRENT_TIMESTAMP,
               error = ?
         WHERE op_id = ?
        """,
        (error[:500], op_id),
    )


async def cancel(op_id: str) -> None:
    await db.execute(
        """
        UPDATE operation_log
           SET status = 'cancelled',
               completed_at = CURRENT_TIMESTAMP
         WHERE op_id = ?
        """,
        (op_id,),
    )


async def recent(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = await db.fetchall(
        """
        SELECT op_id, command, status, article_count, started_at, completed_at, error
          FROM operation_log
         WHERE user_id = ?
         ORDER BY started_at DESC
         LIMIT ?
        """,
        (user_id, limit),
    )
    return [dict(r) for r in rows]
