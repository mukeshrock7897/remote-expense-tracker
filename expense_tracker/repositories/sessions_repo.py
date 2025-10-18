from typing import Optional, List, Dict, Any
from ..db import connect_ctx, now_iso

async def create(user_id: str, title: str) -> str:
    """Insert a session and return id."""
    import uuid
    sid = str(uuid.uuid4())
    ts = now_iso()
    async with connect_ctx() as c:
        await c.execute(
            "INSERT INTO sessions(id, user_id, title, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (sid, user_id, title, "open", ts, ts),
        )
        await c.commit()
    return sid

async def close(session_id: str) -> Optional[str]:
    """Close a session; return user_id if found."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,))
        row = await cur.fetchone()
        if not row:
            return None
        await c.execute(
            "UPDATE sessions SET status='closed', updated_at=? WHERE id=?",
            (now_iso(), session_id),
        )
        await c.commit()
    return row["user_id"]

async def owner(session_id: str) -> Optional[str]:
    """Get user_id for a session."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,))
        row = await cur.fetchone()
        return row["user_id"] if row else None

async def list_for_user(user_id: str, status: Optional[str]) -> List[Dict[str, Any]]:
    """List sessions for a user (optional status)."""
    async with connect_ctx() as c:
        if status:
            cur = await c.execute(
                "SELECT id, title, status, created_at, updated_at FROM sessions WHERE user_id=? AND status=? ORDER BY created_at DESC",
                (user_id, status),
            )
        else:
            cur = await c.execute(
                "SELECT id, title, status, created_at, updated_at FROM sessions WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
