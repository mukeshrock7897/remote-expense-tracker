from typing import Optional, List, Dict, Any
from ..db import connect_ctx, now_iso

async def add(user_id: Optional[str], session_id: Optional[str], kind: str, message: str, progress: Optional[int]) -> int:
    """Insert a notification and return id."""
    async with connect_ctx() as c:
        cur = await c.execute(
            "INSERT INTO notifications(user_id, session_id, kind, message, progress, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, session_id, kind, message, progress, now_iso()),
        )
        await c.commit()
        return cur.lastrowid

async def poll(user_id: str, session_id: Optional[str], after_id: int, limit: int) -> Dict[str, Any]:
    """Fetch notifications after a given id."""
    clauses = ["user_id = ?", "id > ?"]
    params = [user_id, int(after_id)]
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
        rows = await cur.fetchall()
    items = [dict(r) for r in rows]
    last_id = items[-1]["id"] if items else int(after_id)
    return {"items": items, "last_id": last_id}
