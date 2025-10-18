# expense_tracker/services/auth_service.py
from __future__ import annotations

from typing import Optional, Dict, Any

from ..db import ensure_db, connect_ctx
from ..utils.dates import utc_now_iso


class AuthError(Exception):
    """Raised when user/session resolution fails."""


async def upsert_user(user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Create or update a user."""
    await ensure_db()
    async with connect_ctx() as c:
        # upsert user
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        exists = await cur.fetchone()
        if exists:
            await c.execute("UPDATE users SET name = COALESCE(?, name) WHERE id = ?", (name, user_id))
        else:
            await c.execute(
                "INSERT INTO users(id, name, created_at) VALUES (?,?,?)",
                (user_id, name or "", utc_now_iso()),
            )
        await c.commit()
    return {"status": "ok", "user_id": user_id, "name": name or ""}


async def set_default_user_id(user_id: str) -> Dict[str, Any]:
    """Persist default user id in settings table (and ensure the user exists)."""
    await ensure_db()
    async with connect_ctx() as c:
        # ensure user exists
        cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if not await cur.fetchone():
            await c.execute(
                "INSERT INTO users(id, name, created_at) VALUES (?,?,?)",
                (user_id, "", utc_now_iso()),
            )
        await c.execute(
            """
            INSERT INTO settings(key, value) VALUES ('default_user_id', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (user_id,),
        )
        await c.commit()
    return {"status": "ok", "default_user_id": user_id}


async def get_default_user_id() -> Optional[str]:
    """Return default user id, if configured."""
    await ensure_db()
    async with connect_ctx() as c:
        cur = await c.execute("SELECT value FROM settings WHERE key='default_user_id'")
        row = await cur.fetchone()
    return row["value"] if row else None


async def resolve_user(user_id: Optional[str], session_id: Optional[str]) -> str:
    """
    Resolve a concrete user_id based on explicit user_id, session_id,
    or the configured default user (for Inspector convenience).
    """
    await ensure_db()

    # 1) session_id -> user_id
    if session_id:
        async with connect_ctx() as c:
            cur = await c.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,))
            row = await cur.fetchone()
        if not row:
            raise AuthError("session_id not found")
        uid = row["user_id"]
        if user_id and user_id != uid:
            raise AuthError("user_id does not match session owner")
        return uid

    # 2) explicit user_id
    if user_id:
        async with connect_ctx() as c:
            cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
            if not await cur.fetchone():
                raise AuthError("user does not exist; call upsert_user first")
        return user_id

    # 3) fall back to default user (always present by ensure_db bootstrap)
    default_uid = await get_default_user_id()
    if default_uid:
        return default_uid

    # should not happen with our ensure_db bootstrap, but keep a clear error
    raise AuthError("either user_id OR session_id is required (no default user configured)")
