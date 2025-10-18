from typing import Optional, List, Dict, Any
from ..repositories import expenses_repo, notifications_repo
from .auth_service import resolve_user, AuthError

def _coerce_float(v: Any, name: str) -> float:
    """Convert to float or raise ValueError."""
    try:
        return float(v)
    except Exception:
        raise ValueError(f"{name} must be a number")

async def add_expense(date: str, amount: float, category: str, subcategory: str, note: str,
                      user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    """Add expense under a user or session."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}

    try:
        amt = _coerce_float(amount, "amount")
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    if amt < 0:
        return {"status": "error", "message": "amount must be >= 0"}

    exp_id = await expenses_repo.add(uid, date, amt, category, subcategory, note, session_id)
    await notifications_repo.add(uid, session_id, "info", f"Expense added: {category} {amt} on {date}", None)
    return {"status": "ok", "id": exp_id}

async def bulk_add(items: List[Dict[str, Any]], user_id: Optional[str], session_id: Optional[str],
                   batch_size: int) -> Dict[str, Any]:
    """Bulk insert with progress notifications."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}

    total = len(items)
    inserted = 0
    last_nid = await notifications_repo.add(uid, session_id, "progress", f"Bulk import started ({total} items)", 0)

    # Simple batches
    for i in range(0, total, batch_size):
        chunk = items[i:i+batch_size]
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
            await expenses_repo.add(uid, date, amt, category, subcat, note, session_id)
            inserted += 1

        pct = int(round((inserted / max(1, total)) * 100))
        last_nid = await notifications_repo.add(uid, session_id, "progress",
                                                f"Bulk import: {inserted}/{total}", pct)

    await notifications_repo.add(uid, session_id, "info",
                                 f"Bulk import complete. Inserted {inserted}/{total}", None)
    return {"status": "ok", "inserted": inserted, "notifications_until": last_nid}

async def list_expenses(start_date: str, end_date: str, category: Optional[str], subcategory: Optional[str],
                        q: Optional[str], limit: int, offset: int,
                        user_id: Optional[str], session_id: Optional[str]) -> List[Dict[str, Any]]:
    """List expenses (user or session scoped)."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return [{"status": "error", "message": str(e)}]
    return await expenses_repo.list_between(uid, start_date, end_date, category, subcategory, q, session_id, limit, offset)

async def summarize(start_date: str, end_date: str, category: Optional[str], group_by: str,
                    user_id: Optional[str], session_id: Optional[str]) -> List[Dict[str, Any]]:
    """Summarize by category or subcategory."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return [{"status": "error", "message": str(e)}]
    group_col = "category" if group_by == "category" else "subcategory"
    return await expenses_repo.sum_by(uid, start_date, end_date, group_col, category)

async def delete_expense(expense_id: int, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    """Delete an expense if owned by user."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}
    deleted = await expenses_repo.delete_if_owned(expense_id, uid)
    if not deleted:
        return {"status": "error", "message": "not found or forbidden"}
    await notifications_repo.add(uid, session_id, "info", f"Expense {expense_id} deleted", None)
    return {"status": "ok", "deleted": deleted}
