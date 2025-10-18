# expense_tracker/repositories/users_repo.py
from __future__ import annotations

from typing import Optional, Dict, Any

from ..db import connect_ctx
from ..utils.dates import utc_now_iso


async def upsert(user_id: str, name: Optional[str]) -> None:
    async with connect_ctx() as c:
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if await cur.fetchone():
            await c.execute("UPDATE users SET name = COALESCE(?, name) WHERE id = ?", (name, user_id))
        else:
            await c.execute(
                "INSERT INTO users(id, name, created_at) VALUES (?,?,?)",
                (user_id, name or "", utc_now_iso()),
            )
        await c.commit()
