# expense_tracker/server.py
from __future__ import annotations

from fastmcp import FastMCP
import os
from typing import Optional, List, Dict, Any, Literal

# ✅ Use connect_ctx (async context manager) — do NOT import `connect`
from .db import ensure_db, connect_ctx
from .config import GLOBAL_CATEGORIES_PATH, DB_PATH
from .utils.files import read_json_file
from .utils.dates import utc_now_iso
from .utils.logging import setup_logging, log_tool, log_resource

from .services import (
    sessions_service,
    expenses_service,
    categories_service,
    budgets_service,
    export_service,
    notifications_service,
    stats_service,
    maintenance_service,
)

from .services.auth_service import (
    upsert_user as _svc_upsert_user,
    resolve_user,                 # imported to keep parity; used inside services
    set_default_user_id,
    get_default_user_id,
    AuthError,
)

from .repositories import users_repo


# --------------------------------------------------------------------
# Initialize logging ASAP so everything after this point is captured
# --------------------------------------------------------------------
setup_logging()

# MCP server instance
mcp = FastMCP("ExpenseTracker")


# ============================= Users ==============================

@mcp.tool()
@log_tool("upsert_user", redact_keys=())
async def upsert_user(user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Create or update a user record."""
    await ensure_db()
    await users_repo.upsert(user_id, name)
    return {"status": "ok", "user_id": user_id, "name": name or ""}


# ============================ Sessions ============================

@mcp.tool()
@log_tool("create_session", redact_keys=())
async def create_session(user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Create a session for a user."""
    await ensure_db()
    return await sessions_service.create_session(user_id, title)


@mcp.tool()
@log_tool("end_session", redact_keys=())
async def end_session(session_id: str) -> Dict[str, Any]:
    """Close a session."""
    await ensure_db()
    return await sessions_service.end_session(session_id)


@mcp.tool()
@log_tool("list_sessions", redact_keys=())
async def list_sessions(
    user_id: str, status: Optional[Literal["open", "closed"]] = None
) -> List[Dict[str, Any]]:
    """List sessions for a user."""
    await ensure_db()
    return await sessions_service.list_sessions(user_id, status)


# ============================ Expenses ============================

@mcp.tool()
@log_tool("add_expense")
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add an expense (user or session scoped)."""
    await ensure_db()
    return await expenses_service.add_expense(
        date, amount, category, subcategory, note, user_id, session_id
    )


@mcp.tool()
@log_tool("bulk_add_expenses")
async def bulk_add_expenses(
    items: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """Bulk insert expenses with progress notifications."""
    await ensure_db()
    return await expenses_service.bulk_add(items, user_id, session_id, batch_size)


@mcp.tool()
@log_tool("list_expenses", redact_keys=())
async def list_expenses(
    start_date: str,
    end_date: str,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List expenses between two dates (user or session scoped)."""
    await ensure_db()
    return await expenses_service.list_expenses(
        start_date,
        end_date,
        category,
        subcategory,
        q,
        limit,
        offset,
        user_id,
        session_id,
    )


@mcp.tool()
@log_tool("summarize", redact_keys=())
async def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None,
    group_by: Literal["category", "subcategory"] = "category",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Summarize expenses by category or subcategory."""
    await ensure_db()
    return await expenses_service.summarize(
        start_date, end_date, category, group_by, user_id, session_id
    )


@mcp.tool()
@log_tool("delete_expense", redact_keys=())
async def delete_expense(
    expense_id: int,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete an expense if owned by user."""
    await ensure_db()
    return await expenses_service.delete_expense(expense_id, user_id, session_id)


# =========================== Categories ===========================

@mcp.tool()
@log_tool("get_categories", redact_keys=())
async def get_categories() -> Dict[str, Any]:
    """Return global categories.json."""
    await ensure_db()
    return await categories_service.get_global()


@mcp.tool()
@log_tool("set_categories")
async def set_categories(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Set global categories.json (admin)."""
    await ensure_db()
    return await categories_service.set_global(payload)


@mcp.tool()
@log_tool("get_user_categories", redact_keys=())
async def get_user_categories(
    user_id: Optional[str] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get per-user categories or fallback to global."""
    await ensure_db()
    return await categories_service.get_user(user_id, session_id)


@mcp.tool()
@log_tool("set_user_categories")
async def set_user_categories(
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Set per-user categories payload."""
    await ensure_db()
    return await categories_service.set_user(payload, user_id, session_id)


# ============================= Budgets ============================

@mcp.tool()
@log_tool("set_budget")
async def set_budget(
    month: str,
    category: str,
    amount: float,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Upsert a budget row for user/month/category."""
    await ensure_db()
    return await budgets_service.set_budget(month, category, amount, user_id, session_id)


@mcp.tool()
@log_tool("get_budgets", redact_keys=())
async def get_budgets(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    month: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List budgets for user."""
    await ensure_db()
    return await budgets_service.list_budgets(user_id, session_id, month, category)


@mcp.tool()
@log_tool("budget_status", redact_keys=())
async def budget_status(
    month: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Spent vs budget per category for month."""
    await ensure_db()
    return await budgets_service.status(month, user_id, session_id)


# ============== Export / Stats / Maintenance ======================

@mcp.tool()
@log_tool("export_data", redact_keys=())
async def export_data(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Export a user's snapshot."""
    await ensure_db()
    return await export_service.export(user_id, session_id, start_date, end_date)


@mcp.tool()
@log_tool("get_stats", redact_keys=())
async def get_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return counts (user or global)."""
    await ensure_db()
    return await stats_service.stats(user_id)


@mcp.tool()
@log_tool("vacuum_analyze", redact_keys=())
async def vacuum_analyze() -> Dict[str, Any]:
    """Run VACUUM and ANALYZE."""
    await ensure_db()
    return await maintenance_service.vacuum_analyze()


# =========================== Notifications ========================

@mcp.tool()
@log_tool("poll_notifications", redact_keys=())
async def poll_notifications(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    after_id: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    """Fetch notifications after a known id."""
    await ensure_db()
    return await notifications_service.poll(user_id, session_id, after_id, limit)


# ============================== Resources =========================

@mcp.resource("expense://categories", mime_type="application/json")
@log_resource("expense://categories")
async def categories_resource() -> str:
    """Raw global categories JSON string (no DB access)."""
    data = await read_json_file(GLOBAL_CATEGORIES_PATH)
    import json as _json
    return _json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("expense://health", mime_type="application/json")
@log_resource("expense://health")
async def health_resource() -> str:
    """Simple health info (no DB access)."""
    import json as _json
    info = {
        "name": "ExpenseTracker",
        "transport": os.getenv("MCP_TRANSPORT", "stdio"),
        "time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "db_exists": os.path.exists(DB_PATH),
    }
    return _json.dumps(info, ensure_ascii=False, indent=2)


@mcp.resource("expense://schema", mime_type="application/json")
@log_resource("expense://schema")
async def schema_resource() -> str:
    """DB schema snapshot from sqlite_master."""
    await ensure_db()
    import json as _json
    schema: Dict[str, Any] = {}
    # ✅ Use a short-lived async connection context to avoid locks & thread reuse issues
    async with connect_ctx() as c:
        cur = await c.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        rows = await cur.fetchall()
        for r in rows:
            schema[r["name"]] = r["sql"]
    return _json.dumps(schema, ensure_ascii=False, indent=2)


# ======================= Default user helpers =====================

@mcp.tool()
@log_tool(name="set_default_user")
async def set_default_user(user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Set a server-wide default user that will be used when user_id/session_id
    are omitted by clients (e.g., MCP Inspector). Also ensures the user exists.
    """
    await ensure_db()
    # ensure user exists (reuse your service impl)
    await _svc_upsert_user(user_id=user_id, name=name)
    out = await set_default_user_id(user_id)
    return out


@mcp.tool()
@log_tool(name="get_default_user", redact_keys=())
async def get_default_user() -> Dict[str, Any]:
    """Return the currently configured default user id, if any."""
    await ensure_db()
    uid = await get_default_user_id()
    return {"default_user_id": uid}
