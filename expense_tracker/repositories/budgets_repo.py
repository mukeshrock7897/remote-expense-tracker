from typing import Optional, List, Dict, Any
from ..db import connect_ctx

async def upsert(user_id: str, month: str, category: str, amount: float) -> None:
    """Insert or update a budget row."""
    async with connect_ctx() as c:
        await c.execute(
            """
            INSERT INTO budgets(user_id, month, category, amount)
            VALUES (?,?,?,?)
            ON CONFLICT(user_id, month, category) DO UPDATE SET amount=excluded.amount
            """,
            (user_id, month, category, amount),
        )
        await c.commit()

async def list_for_user(user_id: str, month: Optional[str], category: Optional[str]) -> List[Dict[str, Any]]:
    """List budgets for user with optional filters."""
    clauses = ["user_id = ?"]
    params = [user_id]
    if month:
        clauses.append("month = ?")
        params.append(month)
    if category:
        clauses.append("category = ?")
        params.append(category)

    sql = f"SELECT id, user_id, month, category, amount FROM budgets WHERE {' AND '.join(clauses)} ORDER BY month DESC, category ASC"
    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
