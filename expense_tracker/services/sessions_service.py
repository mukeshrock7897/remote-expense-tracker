# expense_tracker/services/sessions_service.py
from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any, Literal

from ..db import ensure_db, connect_ctx
from ..utils.dates import utc_now_iso


async def create_session(user_id: str, title: Optional[str]) -> Dict[str, Any]:
    await ensure_db()

    # ensure user exists
    async with connect_ctx() as c:
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if not await cur.fetchone():
            return {"status": "error", "message": "user does not exist; call upsert_user first"}

        session_id = str(uuid.uuid4())
        now = utc_now_iso()
        await c.execute(
            """
            INSERT INTO sessions(id, user_id, title, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?)
            """,
            (session_id, user_id, title or "", "open", now, now),
        )
        await c.commit()

    return {"status": "ok", "session_id": session_id, "created_at": now}


async def end_session(session_id: str) -> Dict[str, Any]:
    await ensure_db()
    async with connect_ctx() as c:
        cur = await c.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
        if not await cur.fetchone():
            return {"status": "error", "message": "session not found"}

        await c.execute(
            "UPDATE sessions SET status='closed', updated_at=? WHERE id=?",
            (utc_now_iso(), session_id),
        )
        await c.commit()
    return {"status": "ok", "session_id": session_id}


async def list_sessions(user_id: str, status: Optional[Literal["open", "closed"]]) -> List[Dict[str, Any]]:
    await ensure_db()
    async with connect_ctx() as c:
        if status:
            cur = await c.execute(
                """
                SELECT id, title, status, created_at, updated_at
                FROM sessions
                WHERE user_id=? AND status=?
                ORDER BY created_at DESC
                """,
                (user_id, status),
            )
        else:
            cur = await c.execute(
                """
                SELECT id, title, status, created_at, updated_at
                FROM sessions
                WHERE user_id=?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
