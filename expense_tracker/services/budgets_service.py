from typing import Optional, List, Dict, Any
from ..repositories import budgets_repo, expenses_repo
from .auth_service import resolve_user, AuthError

async def set_budget(month: str, category: str, amount: float, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    """Upsert a budget row for a user."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}
    if float(amount) < 0:
        return {"status": "error", "message": "amount must be >= 0"}
    await budgets_repo.upsert(uid, month, category, float(amount))
    return {"status": "ok", "month": month, "category": category, "amount": float(amount)}

async def list_budgets(user_id: Optional[str], session_id: Optional[str], month: Optional[str], category: Optional[str]) -> List[Dict[str, Any]]:
    """List budgets for resolved user."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return [{"status": "error", "message": str(e)}]
    return await budgets_repo.list_for_user(uid, month, category)

async def status(month: str, user_id: Optional[str], session_id: Optional[str]) -> List[Dict[str, Any]]:
    """Spent vs budget per category for month."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return [{"status": "error", "message": str(e)}]
    spent = await expenses_repo.month_spent_by_category(uid, month)
    budgets = {row["category"]: float(row["amount"]) for row in await budgets_repo.list_for_user(uid, month, None)}
    cats = set(spent.keys()) | set(budgets.keys())
    out = []
    for cat in sorted(cats):
        b = budgets.get(cat, 0.0)
        s = spent.get(cat, 0.0)
        out.append({"category": cat, "budget": b, "spent": s, "remaining": b - s})
    return out
