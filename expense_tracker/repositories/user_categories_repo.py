from typing import Optional, Dict, Any
import json
from ..db import connect_ctx

async def get(user_id: str) -> Optional[Dict[str, Any]]:
    """Get per-user categories payload."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT payload FROM user_categories WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None

async def set(user_id: str, payload: Dict[str, Any]) -> None:
    """Set per-user categories payload."""
    import json as _json
    serialized = _json.dumps(payload, ensure_ascii=False)
    async with connect_ctx() as c:
        await c.execute(
            """
            INSERT INTO user_categories(user_id, payload) VALUES (?,?)
            ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload
            """,
            (user_id, serialized),
        )
        await c.commit()
