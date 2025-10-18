# expense_tracker/repositories/notifications_repo.py
from __future__ import annotations

from typing import Optional, List, Dict, Any, Literal

from ..db import connect_ctx
from ..utils.dates import utc_now_iso


async def insert(
    *,
    user_id: Optional[str],
    session_id: Optional[str],
    kind: Literal["info", "warning", "error", "progress"],
    message: str,
    progress: Optional[int] = None,
) -> int:
    """
    Insert a notification row and return its id.
    """
    async with connect_ctx() as c:
        cur = await c.execute(
            """
            INSERT INTO notifications(user_id, session_id, kind, message, progress, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (user_id, session_id, kind, message, progress, utc_now_iso()),
        )
        await c.commit()
        return cur.lastrowid


async def poll(
    *,
    user_id: str,
    session_id: Optional[str],
    after_id: int,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Fetch notifications for a user (optionally narrowed by session),
    with id > after_id, ascending.
    """
    clauses: List[str] = ["user_id = ?", "id > ?"]
    params: List[Any] = [user_id, int(after_id)]
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)

    sql = f"""
      SELECT id, user_id, session_id, kind, message, progress, created_at
      FROM notifications
      WHERE {' AND '.join(clauses)}
      ORDER BY id ASC
      LIMIT ?
    """
    params.append(int(limit))

    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = [dict(r) for r in await cur.fetchall()]

    last_id = rows[-1]["id"] if rows else int(after_id)
    return {"items": rows, "last_id": last_id}
