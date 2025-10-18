from typing import Optional, List, Dict, Any
from ..repositories import sessions_repo, notifications_repo, users_repo

async def create_session(user_id: str, title: Optional[str]) -> Dict[str, Any]:
    """Create a session; user must exist."""
    if not await users_repo.exists(user_id):
        return {"status": "error", "message": "user does not exist; call upsert_user first"}
    sid = await sessions_repo.create(user_id, title or "")
    await notifications_repo.add(user_id, sid, "info", "Session created", None)
    return {"status": "ok", "session_id": sid}

async def end_session(session_id: str) -> Dict[str, Any]:
    """Close session and notify."""
    owner = await sessions_repo.close(session_id)
    if not owner:
        return {"status": "error", "message": "session not found"}
    await notifications_repo.add(owner, session_id, "info", "Session closed", None)
    return {"status": "ok", "session_id": session_id}

async def list_sessions(user_id: str, status: Optional[str]) -> List[Dict[str, Any]]:
    """List sessions for a user."""
    return await sessions_repo.list_for_user(user_id, status)
