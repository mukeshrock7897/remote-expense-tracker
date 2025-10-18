# expense_tracker/utils/logging.py
from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import time
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Set, Tuple, Union, cast

_LOGGER = logging.getLogger("expense_tracker")

# Reserved attributes on LogRecord that must not be provided in extra
_RESERVED_KEYS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "asctime",
}

# Default sensitive keys to redact if found anywhere in dicts
_DEFAULT_SENSITIVE = {
    "authorization", "token", "password", "secret", "key", "api_key", "bearer",
    "auth", "access_token", "refresh_token",
}


def setup_logging() -> None:
    """
    Configure root logging from env:
      LOG_LEVEL  = DEBUG|INFO|WARNING|ERROR (default INFO)
      LOG_FORMAT = console|json (default console)
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "console").lower()

    handler = logging.StreamHandler()
    if fmt == "json":
        formatter = logging.Formatter(
            fmt='{"ts":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter("%(asctime)s | %(levelname)-5s | %(name)s | %(message)s")

    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)


def _safe_extra(extra: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Rename reserved keys and coerce values to something JSON-serializable-ish."""
    if not extra:
        return {}
    out: Dict[str, Any] = {}
    for k, v in extra.items():
        kk = f"x_{k}" if k in _RESERVED_KEYS else k
        try:
            json.dumps(v, default=str)
            out[kk] = v
        except Exception:
            out[kk] = str(v)
    return out


def _redact(obj: Any, sensitive: Set[str]) -> Any:
    """Recursively redact values where dict key matches a sensitive name (case-insensitive)."""
    try:
        if isinstance(obj, Mapping):
            redacted: Dict[str, Any] = {}
            for k, v in obj.items():
                if str(k).lower() in sensitive:
                    redacted[k] = "***REDACTED***"
                else:
                    redacted[k] = _redact(v, sensitive)
            return redacted
        elif isinstance(obj, (list, tuple)):
            return obj.__class__(_redact(x, sensitive) for x in obj)
        else:
            return obj
    except Exception:
        return obj


def _decorate_tool(
    fn: Callable[..., Any],
    *,
    name: Optional[str],
    redact_keys: Set[str],
) -> Callable[..., Any]:
    tool_name = name or getattr(fn, "__name__", "tool")
    is_coro = asyncio.iscoroutinefunction(fn)
    sensitive = set(k.lower() for k in (_DEFAULT_SENSITIVE | redact_keys))

    def _start_payload(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return _redact({"tool_args": args, "tool_kwargs": kwargs}, sensitive)

    if is_coro:
        @functools.wraps(fn)
        async def _async(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            _LOGGER.info("tool_call_start %s", tool_name, extra=_safe_extra(_start_payload(args, kwargs)))
            try:
                result = await cast(Awaitable[Any], fn(*args, **kwargs))
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.info("tool_call_end %s ok", tool_name, extra=_safe_extra({"duration_ms": dur}))
                return result
            except Exception as e:
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.error(
                    "tool_call_end %s error", tool_name,
                    extra=_safe_extra({"duration_ms": dur, "error": repr(e)}),
                )
                raise
        return _async
    else:
        @functools.wraps(fn)
        def _sync(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            _LOGGER.info("tool_call_start %s", tool_name, extra=_safe_extra(_start_payload(args, kwargs)))
            try:
                result = fn(*args, **kwargs)
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.info("tool_call_end %s ok", tool_name, extra=_safe_extra({"duration_ms": dur}))
                return result
            except Exception as e:
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.error(
                    "tool_call_end %s error", tool_name,
                    extra=_safe_extra({"duration_ms": dur, "error": repr(e)}),
                )
                raise
        return _sync


def log_tool(
    _fn: Optional[Callable[..., Any]] = None,
    name: Optional[str] = None,
    redact_keys: Union[Set[str], Tuple[str, ...]] = (),
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for MCP tools.

    Usage:
      @log_tool
      async def add_expense(...): ...

      @log_tool(name="add_expense", redact_keys={"token"})
      async def add_expense(...): ...
    """
    rk: Set[str] = set(redact_keys) if isinstance(redact_keys, (set, tuple)) else set()

    if _fn is not None and callable(_fn):
        # Used as @log_tool
        return _decorate_tool(_fn, name=name, redact_keys=rk)

    # Used as @log_tool(...)
    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _decorate_tool(fn, name=name, redact_keys=rk)

    return _wrap


def _decorate_resource(
    fn: Callable[..., Any],
    *,
    name: Optional[str],
) -> Callable[..., Any]:
    res_name = name or getattr(fn, "__name__", "resource")
    is_coro = asyncio.iscoroutinefunction(fn)

    if is_coro:
        @functools.wraps(fn)
        async def _async(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            _LOGGER.info("resource_read_start %s", res_name)
            try:
                result = await cast(Awaitable[Any], fn(*args, **kwargs))
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.info("resource_read_end %s ok", res_name, extra=_safe_extra({"duration_ms": dur}))
                return result
            except Exception as e:
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.error(
                    "resource_read_end %s error", res_name,
                    extra=_safe_extra({"duration_ms": dur, "error": repr(e)}),
                )
                raise
        return _async
    else:
        @functools.wraps(fn)
        def _sync(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            _LOGGER.info("resource_read_start %s", res_name)
            try:
                result = fn(*args, **kwargs)
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.info("resource_read_end %s ok", res_name, extra=_safe_extra({"duration_ms": dur}))
                return result
            except Exception as e:
                dur = int((time.perf_counter() - start) * 1000)
                _LOGGER.error(
                    "resource_read_end %s error", res_name,
                    extra=_safe_extra({"duration_ms": dur, "error": repr(e)}),
                )
                raise
        return _sync


def log_resource(
    _fn: Optional[Callable[..., Any]] = None,
    name: Optional[str] = None,
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for MCP resources.

    Usage:
      @log_resource
      async def categories_resource(): ...

      @log_resource(name="categories")
      async def categories_resource(): ...
    """
    if _fn is not None and callable(_fn):
        return _decorate_resource(_fn, name=name)

    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _decorate_resource(fn, name=name)

    return _wrap
