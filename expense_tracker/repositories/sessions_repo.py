# expense_tracker/repositories/sessions_repo.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
import uuid

from ..db import connect_ctx
from ..utils.dates import utc_now_iso


async def create(*, user_id: str, title: str = "") -> Dict[str, Any]:
    """
    Create a session row, return {"session_id", "created_at"}.
    """
    sid = str(uuid.uuid4())
    now = utc_now_iso()
    async with connect_ctx() as c:
        await c.execute(
            """
            INSERT INTO sessions(id, user_id, title, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?)
            """,
            (sid, user_id, title, "open", now, now),
        )
        await c.commit()
    return {"session_id": sid, "created_at": now}


async def close(*, session_id: str) -> None:
    """
    Close a session.
    """
    async with connect_ctx() as c:
        await c.execute(
            "UPDATE sessions SET status='closed', updated_at=? WHERE id=?",
            (utc_now_iso(), session_id),
        )
        await c.commit()


async def list_for_user(*, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List sessions for a user, optionally filtered by status.
    """
    params: List[Any] = [user_id]
    sql = """
        SELECT id, title, status, created_at, updated_at
        FROM sessions
        WHERE user_id = ?
    """
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"

    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
