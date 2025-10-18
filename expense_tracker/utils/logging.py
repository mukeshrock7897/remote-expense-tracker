import logging
import json
import os
import time
import uuid
import functools
import inspect
from typing import Any, Dict, Iterable


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S")
        base = f"{ts} | {record.levelname:<7} | {record.name}"
        msg = record.getMessage()
        extra = _extract_extra(record)
        if extra:
            return f"{base} | {msg} | " + " ".join(f"{k}={_to_inline(v)}" for k, v in extra.items())
        return f"{base} | {msg}"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(_extract_extra(record))
        return json.dumps(payload, ensure_ascii=False)


def _extract_extra(record: logging.LogRecord) -> Dict[str, Any]:
    reserved = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
        "relativeCreated", "thread", "threadName", "processName", "process",
    }
    return {k: v for k, v in record.__dict__.items() if k not in reserved}


def _to_inline(v: Any) -> str:
    try:
        s = json.dumps(v, ensure_ascii=False)
        if len(s) > 512:
            s = s[:509] + "..."
        return s
    except Exception:
        return str(v)


def setup_logging() -> None:
    """
    Initialize root logging with sane defaults.
    Env:
      LOG_FORMAT: 'console' (default) or 'json'
      LOG_LEVEL : 'INFO' (default), 'DEBUG', 'WARNING', 'ERROR'
    """
    fmt = os.getenv("LOG_FORMAT", "console").lower()
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler()  # stderr (safe for STDIO transport)
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_ConsoleFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))

    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def log_tool(tool_name: str, redact_keys: Iterable[str] = ("note",)):

    def decorator(fn):
        logger = logging.getLogger(f"tool.{tool_name}")

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            rid = str(uuid.uuid4())[:8]
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            args_summary = _summarize_args(bound.arguments, redact_keys)

            t0 = time.perf_counter()
            logger.info("start", extra={"rid": rid, "args": args_summary})
            try:
                result = await fn(*args, **kwargs)
                dt_ms = int((time.perf_counter() - t0) * 1000)
                ok_summary = _summarize_result(result)
                logger.info("finish", extra={"rid": rid, "ms": dt_ms, "result": ok_summary})
                return result
            except Exception as e:
                dt_ms = int((time.perf_counter() - t0) * 1000)
                logger.exception("error", extra={"rid": rid, "ms": dt_ms, "error": str(e)})
                raise

        return wrapper

    return decorator


def log_resource(resource_name: str):

    def decorator(fn):
        logger = logging.getLogger(f"resource.{resource_name}")

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            rid = str(uuid.uuid4())[:8]
            logger.info("read.start", extra={"rid": rid})
            t0 = time.perf_counter()
            try:
                content = await fn(*args, **kwargs)
                dt_ms = int((time.perf_counter() - t0) * 1000)
                size = len(content.encode("utf-8")) if isinstance(content, str) else None
                logger.info("read.finish", extra={"rid": rid, "ms": dt_ms, "bytes": size})
                return content
            except Exception as e:
                dt_ms = int((time.perf_counter() - t0) * 1000)
                logger.exception("read.error", extra={"rid": rid, "ms": dt_ms, "error": str(e)})
                raise

        return wrapper

    return decorator


def _summarize_args(values: Dict[str, Any], redact_keys: Iterable[str]) -> Dict[str, Any]:
    red = set(k.lower() for k in redact_keys)
    out: Dict[str, Any] = {}
    for k, v in values.items():
        if k.lower() in red:
            out[k] = "***"
            continue
        if k == "items" and isinstance(v, list):
            out[k] = {"type": "list", "len": len(v)}
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
            continue
        try:
            s = json.dumps(v, ensure_ascii=False)
            out[k] = v if len(s) <= 256 else {"type": type(v).__name__, "summary": s[:200] + "..."}
        except Exception:
            out[k] = {"type": type(v).__name__}
    return out


def _summarize_result(result: Any) -> Any:
    if isinstance(result, dict):
        d = dict(result)
        for key in ("inserted", "deleted", "count", "status", "id"):
            if key in d:
                return {k: d[k] for k in d.keys() if k in ("status", "id", "inserted", "deleted", "count")}
        try:
            s = json.dumps(d, ensure_ascii=False)
            return {"type": "dict", "len": len(d), "repr": s[:200] + ("..." if len(s) > 200 else "")}
        except Exception:
            return {"type": "dict", "len": len(d)}
    if isinstance(result, list):
        return {"type": "list", "len": len(result)}
    return result
