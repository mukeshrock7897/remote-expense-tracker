USERS = """
CREATE TABLE IF NOT EXISTS users(
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""

SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions(
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT DEFAULT '',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

EXPENSES = """
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

NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    progress INTEGER,
    created_at TEXT NOT NULL
);
"""

BUDGETS = """
CREATE TABLE IF NOT EXISTS budgets(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    month TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    UNIQUE(user_id, month, category),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

USER_CATEGORIES = """
CREATE TABLE IF NOT EXISTS user_categories(
    user_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

SETTINGS = """
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_cat  ON expenses(user_id, category);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_session   ON expenses(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user      ON sessions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_budgets_user       ON budgets(user_id);",
]
