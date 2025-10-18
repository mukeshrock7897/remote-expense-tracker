# expense_tracker/services/export_service.py
from __future__ import annotations

from typing import Optional, Dict, Any, List

from ..db import ensure_db, connect_ctx
from ..config import GLOBAL_CATEGORIES_PATH
from ..utils.dates import utc_now_iso
from ..utils.files import read_json_file
from .auth_service import resolve_user


async def export(
    user_id: Optional[str],
    session_id: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict[str, Any]:
    """
    Export a user's snapshot (expenses, budgets, categories) as structured JSON.

    Args:
        user_id: User to export for (optional if session_id is provided)
        session_id: Session that resolves to a user (optional if user_id is provided)
        start_date: Lower bound 'YYYY-MM-DD' (inclusive) for expenses filter
        end_date: Upper bound 'YYYY-MM-DD' (inclusive) for expenses filter

    Returns:
        {
          "exported_at": "<iso>",
          "user_id": "<uid>",
          "expenses": [...],
          "budgets": [...],
          "categories": {...}
        }
    """
    await ensure_db()
    uid = await resolve_user(user_id, session_id)

    # ---- Expenses (optionally filtered by date range) ----
    clauses: List[str] = ["user_id = ?"]
    params: List[Any] = [uid]
    if start_date:
        clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        params.append(end_date)

    exp_sql = f"""
        SELECT id, user_id, date, amount, category, subcategory, note, session_id, created_at
        FROM expenses
        WHERE {' AND '.join(clauses)}
        ORDER BY id ASC
    """

    # ---- Budgets (all for that user) ----
    bud_sql = """
        SELECT id, user_id, month, category, amount
        FROM budgets
        WHERE user_id = ?
        ORDER BY month DESC, category ASC
    """

    # ---- Pull from DB ----
    async with connect_ctx() as c:
        cur = await c.execute(exp_sql, params)
        expenses = [dict(r) for r in await cur.fetchall()]

        cur = await c.execute(bud_sql, (uid,))
        budgets = [dict(r) for r in await cur.fetchall()]

        # Try per-user categories first
        cur = await c.execute(
            "SELECT payload FROM user_categories WHERE user_id = ?",
            (uid,),
        )
        row = await cur.fetchone()

    # ---- Categories: per-user override or global fallback ----
    if row and row["payload"]:
        try:
            import json as _json
            categories = _json.loads(row["payload"])
        except Exception:
            categories = await read_json_file(GLOBAL_CATEGORIES_PATH)
    else:
        categories = await read_json_file(GLOBAL_CATEGORIES_PATH)

    return {
        "exported_at": utc_now_iso(),
        "user_id": uid,
        "expenses": expenses,
        "budgets": budgets,
        "categories": categories,
    }
