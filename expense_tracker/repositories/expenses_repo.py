# expense_tracker/repositories/expenses_repo.py
from __future__ import annotations

from typing import Optional, List, Dict, Any

from ..db import connect_ctx
from ..utils.dates import utc_now_iso


async def insert_expense(
    *,
    user_id: str,
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
    session_id: Optional[str] = None,
) -> int:
    """
    Insert a single expense and return its id.
    """
    async with connect_ctx() as c:
        cur = await c.execute(
            """
            INSERT INTO expenses(user_id, date, amount, category, subcategory, note, session_id, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (user_id, date, amount, category, subcategory, note, session_id, utc_now_iso()),
        )
        await c.commit()
        return cur.lastrowid


async def list_expenses_between(
    *,
    user_id: str,
    start_date: str,
    end_date: str,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List expenses between two dates (inclusive) for a user, with filters & pagination.
    """
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


async def summarize_between(
    *,
    user_id: str,
    start_date: str,
    end_date: str,
    group_by: str = "category",
    restrict_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    SUM(amount) grouped by `group_by` in a date range; optionally restrict to a category
    when grouping by subcategory.
    """
    group_column = "category" if group_by == "category" else "subcategory"
    base = f"""
        SELECT {group_column} AS {group_column}, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """
    params: List[Any] = [user_id, start_date, end_date]
    if restrict_category and group_by == "subcategory":
        base += " AND category = ?"
        params.append(restrict_category)

    sql = base + f" GROUP BY {group_column} ORDER BY {group_column} ASC"

    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_if_owned(*, expense_id: int, user_id: str) -> int:
    """
    Delete an expense if it belongs to the given user. Returns number of rows deleted.
    """
    async with connect_ctx() as c:
        cur = await c.execute("SELECT user_id FROM expenses WHERE id = ?", (expense_id,))
        row = await cur.fetchone()
        if not row or row["user_id"] != user_id:
            return 0
        cur = await c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await c.commit()
        return cur.rowcount


async def spent_by_category_for_month(*, user_id: str, month: str) -> Dict[str, float]:
    """
    Return {category: spent} for a user's given month ('YYYY-MM').
    """
    async with connect_ctx() as c:
        cur = await c.execute(
            """
            SELECT category, SUM(amount) AS spent
            FROM expenses
            WHERE user_id = ? AND date LIKE ? || '%'
            GROUP BY category
            """,
            (user_id, month),
        )
        rows = await cur.fetchall()
    return {r["category"]: float(r["spent"] or 0.0) for r in rows}
