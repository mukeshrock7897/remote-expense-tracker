import json
import asyncio
from pathlib import Path
from typing import Any

async def read_json_file(path: str | Path) -> Any:
    """Read JSON file asynchronously."""
    def _load():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return await asyncio.to_thread(_load)

async def write_json_file(path: str | Path, data: Any) -> None:
    """Write JSON file asynchronously."""
    def _dump():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    await asyncio.to_thread(_dump)