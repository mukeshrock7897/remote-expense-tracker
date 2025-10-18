# Remote Expense Tracker MCP Server 🚀

A production-ready, async, multi-tenant **Model Context Protocol (MCP)** server for tracking expenses. Built with **fastmcp** + **aiosqlite**, it includes users, sessions, budgets, notifications, resources, robust logging, and both local (STDIO) and remote (HTTP/SSE) transports. Perfect for use with MCP clients like Claude Desktop or the MCP Inspector.

---

## ✨ Highlights

* Async I/O with **aiosqlite** for concurrency
* **Multi-tenant** data model with `user_id` and session scoping
* Clean, structured **logging** with request IDs, duration, and safe redaction
* **Budgets**, **categories** (global + per-user), **notifications** (with progress), and **exports**
* **Resources** for health, categories, and schema snapshots
* **Transports**: STDIO (local), HTTP (cloud), SSE (alternative)
* Ship-ready project layout and `.gitignore` to keep secrets/artifacts out of GitHub

---

## 🔧 Prerequisites

* Python ≥ 3.12
* [uv](https://github.com/astral-sh/uv) for instant virtualenvs and running the app
* macOS, Linux, or WSL on Windows
* Optional but recommended: Node.js ≥ 18 if you want fastmcp’s built-in Inspector to auto-open in the browser

---

## 🏁 Quickstart (Local Dev with STDIO)

1. Install dependencies in an isolated env and run the server in dev mode:

```
uv run fastmcp dev main.py
```

2. You’ll see the MCP Inspector URL in the logs. Open it, connect, and try the tools and resources.

3. For more verbose or machine-readable logs:

```
LOG_LEVEL=DEBUG LOG_FORMAT=console uv run fastmcp dev main.py
# or
LOG_LEVEL=DEBUG LOG_FORMAT=json uv run fastmcp dev main.py
```

---

## 🧩 How the Data Model Works

* **Users** are explicit. You must call `upsert_user(user_id, name?)` before adding expenses.
* **Sessions** belong to a single user and group related operations. Use `create_session(user_id, title?)`, pass `session_id` in later calls, and close with `end_session(session_id)`.
* **Multi-tenant safety**: Every expense, budget, and notification is stored with the owning `user_id`. Tools accept either `user_id` **or** `session_id`. If both are supplied, they must match; otherwise you get an auth error. This prevents cross-user data leakage.

---

## 🧰 Tools (API)

All tools are async and validated for multi-tenant use. Unless noted, pass either `user_id` or `session_id`.

Users

* `upsert_user(user_id: str, name: Optional[str]) -> {status, user_id, name}`

Sessions

* `create_session(user_id: str, title: Optional[str]) -> {status, session_id, created_at}`
* `end_session(session_id: str) -> {status, session_id}`
* `list_sessions(user_id: str, status: Optional["open"|"closed"]) -> [ ... ]`

Expenses

* `add_expense(date: str, amount: float, category: str, subcategory: str="", note: str="", user_id?: str, session_id?: str) -> {status, id}`
* `bulk_add_expenses(items: List[dict], user_id?: str, session_id?: str, batch_size: int=100) -> {status, inserted, notifications_until}`

  * Sends progress notifications (`kind="progress"`) you can read via `poll_notifications(...)`
* `list_expenses(start_date: str, end_date: str, category?: str, subcategory?: str, q?: str, limit: int=1000, offset: int=0, user_id?: str, session_id?: str) -> [ ... ]`
* `summarize(start_date: str, end_date: str, category?: str, group_by: "category"|"subcategory"="category", user_id?: str, session_id?: str) -> [ ... ]`
* `delete_expense(expense_id: int, user_id?: str, session_id?: str) -> {status, deleted}`

Categories

* `get_categories() -> {categories: [...]}`                                  (global)
* `set_categories(payload: dict) -> {status, count}`                          (global admin)
* `get_user_categories(user_id?: str, session_id?: str) -> {categories: [...]}`  (per-user)
* `set_user_categories(payload: dict, user_id?: str, session_id?: str) -> {status, count}`

Budgets

* `set_budget(month: str, category: str, amount: float, user_id?: str, session_id?: str) -> {status, month, category, amount}`
* `get_budgets(user_id?: str, session_id?: str, month?: str, category?: str) -> [ ... ]`
* `budget_status(month: str, user_id?: str, session_id?: str) -> [ {category, budget, spent, remaining}, ... ]`

Export, Stats, Maintenance

* `export_data(user_id?: str, session_id?: str, start_date?: str, end_date?: str) -> {exported_at, user_id, expenses, budgets, categories}`
* `get_stats(user_id?: str) -> {scope, counts, db_path, size_bytes}`
* `vacuum_analyze() -> {status: "ok"}`

Notifications

* `poll_notifications(user_id?: str, session_id?: str, after_id: int=0, limit: int=100) -> {items: [...], last_id: int}`

---

## 📚 Resources

* `expense://categories` → Global categories JSON (read-only, no DB access)
* `expense://health` → Basic status and metadata (read-only, no DB access)
* `expense://schema` → Live schema snapshot from `sqlite_master` (read-only)

---

## 📝 Example Workflows

Create a user and session

1. `upsert_user({"user_id":"mukesh", "name":"Mukesh Yadav"})`
2. `create_session({"user_id":"mukesh", "title":"October tracking"})` → remember `session_id`

Add expenses

* `add_expense({"session_id":"...", "date":"2025-10-18", "amount":199.0, "category":"shopping", "subcategory":"electronics_gadgets", "note":"keyboard"})`

Summarize and budget

* `summarize({"session_id":"...", "start_date":"2025-10-01", "end_date":"2025-10-31", "group_by":"category"})`
* `set_budget({"user_id":"mukesh", "month":"2025-10", "category":"shopping", "amount":5000})`
* `budget_status({"user_id":"mukesh", "month":"2025-10"})`

Export

* `export_data({"user_id":"mukesh", "start_date":"2025-10-01", "end_date":"2025-10-31"})`

Notifications

* `bulk_add_expenses({"session_id":"...", "items":[...]})`
* `poll_notifications({"session_id":"...", "after_id":0})`

---

## 🗂 Project Layout Overview

* `main.py` is the entrypoint that imports and runs the MCP server
* `expense_tracker/server.py` defines tools and resources and wires logging
* `expense_tracker/db.py` opens connections and ensures schema (WAL, timeouts, indices)
* `expense_tracker/schema.py` contains DDL strings for tables and indices
* `expense_tracker/services/*` implement business logic (sessions, expenses, budgets, exports, notifications, stats, maintenance)
* `expense_tracker/repositories/*` contain DB access functions
* `expense_tracker/utils/*` provide helpers (dates, files, logging)
* `categories.json` ships global category defaults (your hierarchical set)
* `expenses.db` is created automatically at runtime (ignored by Git)

---

## 🪵 Logging

* Choose format with `LOG_FORMAT=console` or `LOG_FORMAT=json`
* Set level with `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`
* Every tool/resource call logs `start` and `finish` with a short request id and duration; errors include structured stacktraces
* Large payloads (like `items` in `bulk_add_expenses`) are summarized, and sensitive keys can be redacted

Examples (console):

```
2025-10-18 19:42:10 | INFO    | tool.add_expense | start | rid="9f3a2a1b" args={"date":"2025-10-18","amount":120.0,"category":"shopping","user_id":"mukesh"}
2025-10-18 19:42:10 | INFO    | tool.add_expense | finish | rid="9f3a2a1b" ms=18 result={"status":"ok","id":42}
```

---

## 🌐 Running as a Remote Server

The server supports HTTP and SSE transports via environment variables in `main.py`.

HTTP mode (cloud):

```
MCP_TRANSPORT=http HOST=0.0.0.0 PORT=8000 LOG_LEVEL=INFO uv run python main.py
```

The endpoint will be available at:

```
http://HOST:PORT/mcp
```

You can change the path:

```
MCP_TRANSPORT=http MCP_HTTP_PATH=/mcp LOG_LEVEL=INFO uv run python main.py
```

SSE mode:

```
MCP_TRANSPORT=sse HOST=0.0.0.0 PORT=8000 uv run python main.py
```

Local STDIO (default):

```
uv run fastmcp dev main.py
```

⚠️ If you expose HTTP/SSE publicly, place it behind a reverse proxy and add authentication at the edge. This server is designed to be embedded by trusted MCP clients and does not perform user authentication by itself.

---

## 🖥 Using with MCP Clients

Claude Desktop and other MCP clients typically support adding local STDIO servers or remote HTTP endpoints. For local development, the dev command already launches an MCP Inspector. If your client has a server registry UI, point it to run the command:

```
uv run fastmcp run main.py --no-banner
```

Or register the HTTP endpoint you started with `MCP_TRANSPORT=http`. Client UIs differ slightly; consult your client’s documentation for adding custom servers.

---

## 🗃 Database Behavior

* SQLite in **WAL** mode with `busy_timeout` to reduce “database is locked”
* Indices on user/date/category/session for good default performance
* Single-flight schema initialization to avoid thread-start errors
* File location: `expenses.db` at repo root by default (ignored by Git)
* You can move the DB by changing the path in `expense_tracker/config.py`

Backups and portability:

* Use `export_data(...)` for a full JSON export of expenses, budgets, and categories
* Restore by ingesting the JSON and writing expenses back through `bulk_add_expenses(...)`

---

## 🔐 Git Hygiene

A `.gitignore` is included that excludes:

* `expenses.db` and SQLite WAL/SHM files
* virtual environments, caches, logs, tokens, and local env files
  If you accidentally committed artifacts before adding `.gitignore`, untrack them with:

```
git rm -r --cached expenses.db __pycache__ .venv logs node_modules || true
git add -A
git commit -m "chore: apply .gitignore and clean artifacts"
```

---

## 🧪 Troubleshooting

“database is locked”

* This project configures WAL and `busy_timeout` and uses a safe connection context. If you still see locks, ensure no long-running transactions are holding write locks, and prefer chunked `bulk_add_expenses` with the default `batch_size`.

“threads can only be started once”

* You’ll get this if an `aiosqlite` connection is awaited twice. The code uses a dedicated `connect_ctx()` context manager that avoids this pitfall.

Inspector shows errors reading `expense://schema`

* This was caused by double-await connection patterns; the current code fixes it by ensuring single connection startup per context.

Inspector starts but shows little detail

* Increase verbosity: `LOG_LEVEL=DEBUG LOG_FORMAT=console uv run fastmcp dev main.py`

Node npx warnings

* Some features that auto-open the Inspector may use Node tooling. If you see “npx not found,” install Node ≥ 18 or open the Inspector URL manually.

---

## 🔒 Security Notes

* This is a multi-tenant server enforcing per-user isolation at the data layer. It does **not** implement network authentication; for remote deployments use firewalls, reverse proxies, or mTLS.
* Sanitized logging avoids dumping large user payloads or sensitive fields. You can extend redaction rules in `expense_tracker/utils/logging.py`.

---

## 🧱 Contributing

* Keep tools small and pure async
* Put DB access in repositories, business rules in services, thin glue in `server.py`
* Add indices before shipping new query patterns
* Prefer JSON resources that avoid DB access for fast health checks

---

## ✅ License

Choose and add a license file if you plan to distribute. MIT is a common, permissive choice.

---

## 🎯 Recap

You can clone, run, and test locally with a single command:

```
uv run fastmcp dev main.py
```

Then connect via the Inspector, create a user, start a session, add expenses, set budgets, and view summaries and exports. For cloud use, flip `MCP_TRANSPORT=http`, bind to `0.0.0.0`, and place behind an authenticated proxy. Logging is clean and configurable, and Git won’t leak your local DB or secrets.