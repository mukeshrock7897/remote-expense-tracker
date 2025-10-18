# expense_tracker/db.py
from __future__ import annotations

import os
import asyncio
import sqlite3
from typing import AsyncIterator, Optional

import aiosqlite

from .config import DB_PATH
from .utils.dates import utc_now_iso

# -----------------------------------------------------------------------------
# One-time initialization guard
# -----------------------------------------------------------------------------
_init_lock = asyncio.Lock()
_initialized = False


class _ConnectWrapper:
    """
    Async context manager that yields a brand new aiosqlite connection
    with sensible pragmas (WAL, FK ON) and row_factory set to sqlite3.Row.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def __aenter__(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA journal_mode = WAL;")
        self._conn = conn
        return conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            # If caller forgot to commit, we still close cleanly.
            await self._conn.close()
            self._conn = None


def connect_ctx() -> _ConnectWrapper:
    """
    Factory for a short-lived async connection context. Always create a fresh
    connection per usage to avoid 'threads can only be started once' and to
    minimize lock contention.
    """
    return _ConnectWrapper(str(DB_PATH))


async def ensure_db() -> None:
    """
    Create tables and indices if missing. Also auto-provision a default user
    if requested via environment (DEFAULT_USER_ID or AUTO_DEFAULT_USER_ID),
    and save it into settings.default_user_id for Inspector convenience.
    """
    global _initialized
    if _initialized:
        return

    async with _init_lock:
        if _initialized:
            return

        # Create schema
        async with connect_ctx() as c:
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS users(
                    id TEXT PRIMARY KEY,
                    name TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions(
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    status TEXT NOT NULL,          -- 'open' | 'closed'
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    session_id TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    kind TEXT NOT NULL,            -- 'info'|'warning'|'error'|'progress'
                    message TEXT NOT NULL,
                    progress INTEGER,
                    created_at TEXT NOT NULL
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    month TEXT NOT NULL,           -- 'YYYY-MM'
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    UNIQUE(user_id, month, category),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS user_categories(
                    user_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS settings(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

            # Indices
            await c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_cat ON expenses(user_id, category);")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_session ON expenses(session_id);")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id);")

            # --- Auto default user bootstrap (for Inspector/dev convenience) ---
            # Read env or fall back to 'local-dev' in dev usage
            default_uid = (
                os.getenv("DEFAULT_USER_ID")
                or os.getenv("AUTO_DEFAULT_USER_ID")
                or "local-dev"
            )

            # Only set if not already configured
            cur = await c.execute("SELECT value FROM settings WHERE key='default_user_id'")
            row = await cur.fetchone()
            if not row:
                # ensure user exists
                now = utc_now_iso()
                cur = await c.execute("SELECT 1 FROM users WHERE id = ?", (default_uid,))
                exists = await cur.fetchone()
                if not exists:
                    await c.execute(
                        "INSERT INTO users(id, name, created_at) VALUES (?,?,?)",
                        (default_uid, "", now),
                    )
                await c.execute(
                    """
                    INSERT INTO settings(key, value) VALUES ('default_user_id', ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (default_uid,),
                )

            await c.commit()

        _initialized = True
