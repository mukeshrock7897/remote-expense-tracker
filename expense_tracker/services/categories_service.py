from typing import Dict, Any, Optional
from ..config import GLOBAL_CATEGORIES_PATH
from ..repositories import user_categories_repo
from ..utils.files import read_json_file, write_json_file
from .auth_service import resolve_user, AuthError

async def get_global() -> Dict[str, Any]:
    """Return global categories.json (hierarchical)."""
    return await read_json_file(GLOBAL_CATEGORIES_PATH)

async def set_global(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Overwrite global categories.json."""
    await write_json_file(GLOBAL_CATEGORIES_PATH, payload)
    return {"status": "ok", "count": sum(len(v) for v in payload.values())}

async def get_user(user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    """Return per-user categories if set, else global."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}
    data = await user_categories_repo.get(uid)
    return data or await get_global()

async def set_user(payload: Dict[str, Any], user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    """Set per-user categories payload."""
    try:
        uid = await resolve_user(user_id, session_id)
    except AuthError as e:
        return {"status": "error", "message": str(e)}
    await user_categories_repo.set(uid, payload)
    return {"status": "ok", "count": sum(len(v) for v in payload.values())}
