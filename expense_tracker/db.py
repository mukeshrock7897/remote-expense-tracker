import sqlite3
import asyncio
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from .config import DB_PATH, GLOBAL_CATEGORIES_PATH
from . import schema
from .utils.dates import utc_now_iso
from .utils.files import write_json_file

_init_done = False
_init_lock = asyncio.Lock()

async def _open_raw() -> aiosqlite.Connection:
    """Create connection object but do NOT wrap it in an async with again."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Pragmas to improve concurrency & reduce 'database is locked'
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.execute("PRAGMA synchronous = NORMAL;")
    await conn.execute("PRAGMA busy_timeout = 5000;")  # wait up to 5s on locks
    return conn

@asynccontextmanager
async def connect_ctx():
    """Safe async context manager for DB connections."""
    conn = await _open_raw()
    try:
        yield conn
    finally:
        await conn.close()

# Backward compat (do NOT use inside 'async with'): only use directly (no ctx manager).
async def connect() -> aiosqlite.Connection:
    """Return an initialized connection. Do NOT use with 'async with'; close it yourself."""
    return await _open_raw()

async def ensure_db() -> None:
    """Create tables, indexes, and global categories if missing (idempotent & single-flight)."""
    global _init_done
    if _init_done:
        return
    async with _init_lock:
        if _init_done:
            return

        async with connect_ctx() as c:
            await c.execute(schema.USERS)
            await c.execute(schema.SESSIONS)
            await c.execute(schema.EXPENSES)
            await c.execute(schema.NOTIFICATIONS)
            await c.execute(schema.BUDGETS)
            await c.execute(schema.USER_CATEGORIES)
            await c.execute(schema.SETTINGS)
            for ddl in schema.INDEXES:
                await c.execute(ddl)
            await c.commit()

        # Ensure global categories.json exists (hierarchical schema you ship in repo root)
        if not Path(GLOBAL_CATEGORIES_PATH).exists():
            await write_json_file(GLOBAL_CATEGORIES_PATH, {"misc": ["uncategorized", "other"]})

        _init_done = True

def now_iso() -> str:
    """Current UTC in ISO string."""
    return utc_now_iso()
