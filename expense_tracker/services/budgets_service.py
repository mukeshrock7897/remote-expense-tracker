# expense_tracker/services/budgets_service.py
from __future__ import annotations

from typing import Optional, List, Dict, Any

from ..db import ensure_db, connect_ctx
from ..utils.dates import utc_now_iso  # not strictly needed, but handy to keep
from .auth_service import resolve_user


def _coerce_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{name} must be a number")


async def set_budget(
    month: str,
    category: str,
    amount: float,
    user_id: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    """
    Upsert a budget row for a user/month/category.
    """
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    amt = _coerce_float(amount, "amount")
    if amt < 0:
        return {"status": "error", "message": "amount must be >= 0"}

    async with connect_ctx() as c:
        await c.execute(
            """
            INSERT INTO budgets(user_id, month, category, amount)
            VALUES (?,?,?,?)
            ON CONFLICT(user_id, month, category) DO UPDATE SET amount=excluded.amount
            """,
            (uid, month, category, amt),
        )
        await c.commit()

    return {"status": "ok", "month": month, "category": category, "amount": amt}


async def list_budgets(
    user_id: Optional[str],
    session_id: Optional[str],
    month: Optional[str],
    category: Optional[str],
) -> List[Dict[str, Any]]:
    """
    List budgets for a user, with optional month/category filters.
    """
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    clauses, params = ["user_id = ?"], [uid]
    if month:
        clauses.append("month = ?")
        params.append(month)
    if category:
        clauses.append("category = ?")
        params.append(category)

    sql = f"""
        SELECT id, user_id, month, category, amount
        FROM budgets
        WHERE {' AND '.join(clauses)}
        ORDER BY month DESC, category ASC
    """

    async with connect_ctx() as c:
        cur = await c.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def status(
    month: str,
    user_id: Optional[str],
    session_id: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Compute spent vs. budget per category for a user's month ('YYYY-MM').
    """
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    async with connect_ctx() as c:
        # Spent in that month by category
        cur = await c.execute(
            """
            SELECT category, SUM(amount) AS spent
            FROM expenses
            WHERE user_id = ? AND date LIKE ? || '%'
            GROUP BY category
            """,
            (uid, month),
        )
        spent_rows = {r["category"]: float(r["spent"] or 0.0) for r in await cur.fetchall()}

        # Budgets for that month
        cur = await c.execute(
            "SELECT category, amount FROM budgets WHERE user_id = ? AND month = ?",
            (uid, month),
        )
        budgets = {r["category"]: float(r["amount"]) for r in await cur.fetchall()}

    cats = set(budgets.keys()) | set(spent_rows.keys())
    out: List[Dict[str, Any]] = []
    for cat in sorted(cats):
        b = budgets.get(cat, 0.0)
        s = spent_rows.get(cat, 0.0)
        out.append({"category": cat, "budget": b, "spent": s, "remaining": b - s})
    return out
