from typing import Optional, Dict, Any, List
from ..repositories import budgets_repo
from ..repositories.expenses_repo import list_between
from ..repositories.user_categories_repo import get as get_user_cats
from ..utils.files import read_json_file
from ..config import GLOBAL_CATEGORIES_PATH
from .auth_service import resolve_user, AuthError

async def export(user_id: Optional[str], session_id: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    """Export a user's data snapshot (expenses, budgets, categories)."""
    from ..utils.dates import utc_now_iso
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}

    expenses: List[Dict[str, Any]] = await list_between(uid, start_date or "0000-01-01", end_date or "9999-12-31",
                                                         None, None, None, None, 10_000_000, 0)
    budgets = await budgets_repo.list_for_user(uid, None, None)
    cats = await get_user_cats(uid) or await read_json_file(GLOBAL_CATEGORIES_PATH)
    return {
        "exported_at": utc_now_iso(),
        "user_id": uid,
        "expenses": expenses,
        "budgets": budgets,
        "categories": cats,
    }
