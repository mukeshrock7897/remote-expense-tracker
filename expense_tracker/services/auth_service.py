from typing import Optional
from ..repositories import users_repo, sessions_repo

class AuthError(Exception):
    """Raised when user/session context cannot be resolved."""

async def resolve_user(user_id: Optional[str], session_id: Optional[str]) -> str:
    """Resolve and return user_id; ensure ownership if both supplied."""
    if session_id:
        owner = await sessions_repo.owner(session_id)
        if not owner:
            raise AuthError("session_id not found")
        if user_id and user_id != owner:
            raise AuthError("user_id does not match session owner")
        uid = owner
    else:
        if not user_id:
            raise AuthError("either user_id OR session_id is required")
        uid = user_id

    if not await users_repo.exists(uid):
        raise AuthError("user does not exist; call upsert_user(user_id, name?) first")
    return uid
