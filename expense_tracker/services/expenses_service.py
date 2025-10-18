# expense_tracker/services/expenses_service.py
from __future__ import annotations

from typing import Optional, List, Dict, Any, Literal

from ..db import ensure_db, connect_ctx
from ..utils.dates import utc_now_iso
from .auth_service import resolve_user


def _coerce_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{name} must be a number")


async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str,
    note: str,
    user_id: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    """Insert a single expense, committing the write."""
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    amt = _coerce_float(amount, "amount")
    if amt < 0:
        return {"status": "error", "message": "amount must be >= 0"}

    async with connect_ctx() as c:
        cur = await c.execute(
            """
            INSERT INTO expenses(user_id, date, amount, category, subcategory, note, session_id, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (uid, date, amt, category, subcategory, note, session_id, utc_now_iso()),
        )
        await c.commit()
        exp_id = cur.lastrowid

    return {"status": "ok", "id": exp_id}


async def bulk_add(
    items: List[Dict[str, Any]],
    user_id: Optional[str],
    session_id: Optional[str],
    batch_size: int,
) -> Dict[str, Any]:
    """Bulk insert with commits per chunk for reliability."""
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    total = len(items)
    inserted = 0

    async with connect_ctx() as c:
        for i in range(0, total, max(1, batch_size)):
            chunk = items[i : i + batch_size]
            for it in chunk:
                date = str(it.get("date"))
                try:
                    amt = _coerce_float(it.get("amount", 0.0), "amount")
                except ValueError:
                    continue
                if amt < 0:
                    continue
                category = str(it.get("category", "Other"))
                subcat = str(it.get("subcategory", "")) if it.get("subcategory") is not None else ""
                note = str(it.get("note", "")) if it.get("note") is not None else ""
                await c.execute(
                    """
                    INSERT INTO expenses(user_id, date, amount, category, subcategory, note, session_id, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (uid, date, amt, category, subcat, note, session_id, utc_now_iso()),
                )
                inserted += 1
            await c.commit()

    return {"status": "ok", "inserted": inserted}


async def list_expenses(
    start_date: str,
    end_date: str,
    category: Optional[str],
    subcategory: Optional[str],
    q: Optional[str],
    limit: int,
    offset: int,
    user_id: Optional[str],
    session_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Read-only listing, ordered by id ASC."""
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    clauses = ["user_id = ?", "date BETWEEN ? AND ?"]
    params: List[Any] = [uid, start_date, end_date]

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


async def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str],
    group_by: Literal["category", "subcategory"],
    user_id: Optional[str],
    session_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Aggregation by category OR subcategory."""
    await ensure_db()
    uid = await resolve_user(user_id, session_id)
    group_column = "category" if group_by == "category" else "subcategory"

    base = f"""
        SELECT {group_column} AS {group_column}, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """
    params: List[Any] = [uid, start_date, end_date]
    if category and group_by == "subcategory":
        base += " AND category = ?"
        params.append(category)
    sql = base + f" GROUP BY {group_column} ORDER BY {group_column} ASC"

    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def delete_expense(
    expense_id: int,
    user_id: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    """Delete only if the expense belongs to the resolved user."""
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    async with connect_ctx() as c:
        cur = await c.execute("SELECT user_id FROM expenses WHERE id = ?", (expense_id,))
        row = await cur.fetchone()
        if not row:
            return {"status": "error", "message": "expense not found"}
        if row["user_id"] != uid:
            return {"status": "error", "message": "forbidden: expense not owned by user"}

        cur = await c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await c.commit()
        deleted = cur.rowcount

    return {"status": "ok", "deleted": deleted}
