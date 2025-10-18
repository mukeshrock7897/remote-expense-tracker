from typing import Optional, List, Dict, Any
from ..db import connect_ctx, now_iso

async def add(user_id: str, date: str, amount: float, category: str, subcategory: str, note: str, session_id: Optional[str]) -> int:
    """Insert expense and return id."""
    async with connect_ctx() as c:
        cur = await c.execute(
            """
            INSERT INTO expenses(user_id, date, amount, category, subcategory, note, session_id, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (user_id, date, amount, category, subcategory, note, session_id, now_iso()),
        )
        await c.commit()
        return cur.lastrowid

async def delete_if_owned(expense_id: int, user_id: str) -> int:
    """Delete expense if owned by user; return rows affected."""
    async with connect_ctx() as c:
        cur = await c.execute("SELECT user_id FROM expenses WHERE id = ?", (expense_id,))
        row = await cur.fetchone()
        if not row or row["user_id"] != user_id:
            return 0
        cur = await c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await c.commit()
        return cur.rowcount

async def list_between(user_id: str, start_date: str, end_date: str,
                       category: Optional[str], subcategory: Optional[str], q: Optional[str],
                       session_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
    """List user expenses with filters."""
    clauses = ["user_id = ?", "date BETWEEN ? AND ?"]
    params: List[Any] = [user_id, start_date, end_date]
    if category:
        clauses.append("category = ?")
        params.append(category)
    if subcategory:
        clauses.append("subcategory = ?")
        params.append(subcategory)
    if q:
        clauses.append("note LIKE ?")
        params.append(f"%{q}%")
    if session_id:
        clauses.append("IFNULL(session_id,'') = ?")
        params.append(session_id)
    sql = f"""
        SELECT id, user_id, date, amount, category, subcategory, note, session_id, created_at
        FROM expenses
        WHERE {' AND '.join(clauses)}
        ORDER BY id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([int(limit), int(offset)])
    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

async def sum_by(user_id: str, start_date: str, end_date: str, group_col: str, filter_category: Optional[str]) -> List[Dict[str, Any]]:
    """Aggregate sums grouped by category or subcategory."""
    base = f"""
        SELECT {group_col} AS {group_col}, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """
    params: List[Any] = [user_id, start_date, end_date]
    if filter_category and group_col == "subcategory":
        base += " AND category = ?"
        params.append(filter_category)
    sql = base + f" GROUP BY {group_col} ORDER BY {group_col} ASC"
    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

async def month_spent_by_category(user_id: str, month: str) -> Dict[str, float]:
    """Sum spent per category for a month 'YYYY-MM'."""
    async with connect_ctx() as c:
        cur = await c.execute(
            "SELECT category, SUM(amount) AS spent FROM expenses WHERE user_id = ? AND date LIKE ? || '%' GROUP BY category",
            (user_id, month),
        )
        rows = await cur.fetchall()
    return {r["category"]: float(r["spent"] or 0.0) for r in rows}
