from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, TextIO

_REDACT = "***"


def _is_secret_key(key: str) -> bool:
    k = key.strip().lower()

    exact = {
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "password",
        "passwd",
        "pwd",
        "authorization",
        "cookie",
        "session",
        "private_key",
        "privatekey",
    }
    if k in exact:
        return True

    if any(x in k for x in ("token", "secret", "password", "authorization", "bearer")):
        return True

    if k.endswith("_key") or k.endswith("-key") or k.endswith("_apikey") or k.endswith("-apikey"):
        return True

    return False


def _iter_leaf_values(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_leaf_values(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from _iter_leaf_values(v)
    else:
        yield obj


def _collect_secret_values(fields: Any, out: Set[str]) -> None:
    if isinstance(fields, dict):
        for k, v in fields.items():
            if isinstance(k, str) and _is_secret_key(k):
                for leaf in _iter_leaf_values(v):
                    if leaf is None:
                        continue
                    try:
                        out.add(leaf if isinstance(leaf, str) else str(leaf))
                    except Exception:
                        pass
            _collect_secret_values(v, out)
    elif isinstance(fields, (list, tuple, set)):
        for v in fields:
            _collect_secret_values(v, out)


def _redact(obj: Any, secret_values: Set[str]) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and _is_secret_key(k):
                out[k] = _REDACT
            else:
                out[k] = _redact(v, secret_values)
        return out

    if isinstance(obj, (list, tuple)):
        return [_redact(v, secret_values) for v in obj]

    if isinstance(obj, set):
        return [_redact(v, secret_values) for v in obj]

    if secret_values:
        try:
            s = obj if isinstance(obj, str) else str(obj)
            if s in secret_values:
                return _REDACT
        except Exception:
            pass

    return obj


def _contains_secret_value(obj: Any, secret_values: Set[str]) -> bool:
    if not secret_values:
        return False
    if isinstance(obj, dict):
        return any(_contains_secret_value(v, secret_values) for v in obj.values())
    if isinstance(obj, (list, tuple, set)):
        return any(_contains_secret_value(v, secret_values) for v in obj)
    try:
        s = obj if isinstance(obj, str) else str(obj)
        return s in secret_values
    except Exception:
        return False


class StructuredLogger:
    _LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def __init__(self, log_file: Optional[Path] = None, level: str = "INFO", stream: Optional[TextIO] = None):
        self.log_file = Path(log_file) if log_file else None
        self.level = (level or "INFO").upper()
        self.stream = stream or sys.stdout

    def debug(self, event: str, **fields: Any) -> None:
        self._log("DEBUG", event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._log("INFO", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._log("WARNING", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._log("ERROR", event, **fields)

    def _enabled(self, level: str) -> bool:
        return self._LEVELS.get(level, 20) >= self._LEVELS.get(self.level, 20)

    def _log(self, level: str, event: str, **fields: Any) -> None:
        lvl = (level or "INFO").upper()
        if not self._enabled(lvl):
            return

        secret_values: Set[str] = set()
        _collect_secret_values(fields, secret_values)

        now_ms = int(time.time() * 1000)
        record: Dict[str, Any] = {
            "timestamp": now_ms,
            "ts": now_ms,           # 互換用に残す
            "level": lvl,
            "logger":"compack-structured-logger-v1",    # logger name 必須
            "event": event,
            **fields,
        }

        safe = _redact(record, secret_values)
        if _contains_secret_value(safe, secret_values):
            safe = _redact(safe, secret_values)

        line = json.dumps(safe, ensure_ascii=True, separators=(",", ":"), default=str)

        self.stream.write(line + "\n")
        self.stream.flush()

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

