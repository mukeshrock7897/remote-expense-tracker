# expense_tracker/config.py
import os
from pathlib import Path

# Base directory (repo root for local; /app in container)
BASE_DIR = Path(os.getenv("APP_BASE_DIR", Path(__file__).resolve().parents[1]))

# Data directory (mount a volume here in cloud)
DATA_DIR = Path(os.getenv("APP_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite DB path (override with EXPENSE_DB_PATH)
DB_PATH = Path(os.getenv("EXPENSE_DB_PATH", DATA_DIR / "expenses.db"))

# Global categories.json (override with CATEGORIES_PATH)
GLOBAL_CATEGORIES_PATH = Path(os.getenv("CATEGORIES_PATH", BASE_DIR / "categories.json"))

# HTTP transport defaults (used by main.py)
HTTP_HOST = os.getenv("HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("PORT", "8000"))
HTTP_PATH = os.getenv("MCP_HTTP_PATH", "/mcp")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")
PYTHON_UNBUFFERED = os.getenv("PYTHONUNBUFFERED", "1")
