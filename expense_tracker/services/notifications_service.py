from typing import Optional, Dict, Any
from ..repositories import notifications_repo
from .auth_service import resolve_user, AuthError

async def poll(user_id: Optional[str], session_id: Optional[str], after_id: int, limit: int) -> Dict[str, Any]:
    """Poll notifications for a user, optionally for a session."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}
    return await notifications_repo.poll(uid, session_id, after_id, limit)
