import os
from typing import Optional, Dict, Any
from ..db import connect_ctx
from ..config import DB_PATH

async def stats(user_id: Optional[str]) -> Dict[str, Any]:
    """Return counts; user-scoped if user_id provided, else global."""
    async with connect_ctx() as c:
        if user_id:
            cur = await c.execute("SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,))
            exp = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?", (user_id,))
            ses = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ?", (user_id,))
            noti = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM budgets WHERE user_id = ?", (user_id,))
            bud = (await cur.fetchone())["n"]
            scope = "user"
        else:
            cur = await c.execute("SELECT COUNT(*) AS n FROM expenses")
            exp = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM sessions")
            ses = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM notifications")
            noti = (await cur.fetchone())["n"]
            cur = await c.execute("SELECT COUNT(*) AS n FROM budgets")
            bud = (await cur.fetchone())["n"]
            scope = "global"
    return {
        "scope": scope,
        "counts": {"expenses": exp, "sessions": ses, "notifications": noti, "budgets": bud},
        "db_path": str(DB_PATH),
        "size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
    }
