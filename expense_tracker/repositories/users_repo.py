from typing import Optional
from ..db import connect_ctx, now_iso

async def upsert(user_id: str, name: Optional[str]) -> None:
    """Create or update a user."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        exists = await cur.fetchone()
        if exists:
            await c.execute("UPDATE users SET name = COALESCE(?, name) WHERE id = ?", (name, user_id))
        else:
            await c.execute(
                "INSERT INTO users(id, name, created_at) VALUES (?,?,?)",
                (user_id, name or "", now_iso()),
            )
        await c.commit()

async def exists(user_id: str) -> bool:
    """Check if a user exists."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        return (await cur.fetchone()) is not None
