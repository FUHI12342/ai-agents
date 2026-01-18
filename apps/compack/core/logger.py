from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict

import structlog


class StructuredLogger:
    """structlog を用いた構造化ロガー."""

    SECRET_KEYS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "API_KEY")

    def __init__(self, log_file: Path | None = None, level: str = "INFO"):
        self.log_file = Path(log_file) if log_file else None
        self.level = level.upper()
        self.logger = self._setup_logger()

    def _setup_logger(self):
        level_value = getattr(logging, self.level, logging.INFO)
        handlers = [logging.StreamHandler(sys.stdout)]
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.log_file, encoding="utf-8"))

        logging.basicConfig(
            format="%(message)s",
            handlers=handlers,
            level=level_value,
            force=True,
        )

        def add_logger_name(_, __, event_dict: dict) -> dict:
            event_dict.setdefault("logger", "compack")
            return event_dict

        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                add_logger_name,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        return structlog.get_logger("compack")

    def _mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def redact(key: str, value: Any) -> Any:
            if isinstance(value, dict):
                return {k: redact(k, v) for k, v in value.items()}
            if any(token.lower() in key.lower() for token in self.SECRET_KEYS):
                return "***"
            if isinstance(value, str) and any(token.lower() in value.lower() for token in self.SECRET_KEYS):
                return "***"
            return value

        return {k: redact(k, v) for k, v in data.items()}

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, **self._mask_secrets(kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, **self._mask_secrets(kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, **self._mask_secrets(kwargs))

    def error(self, message: str, error: Exception | None = None, **kwargs: Any) -> None:
        data = self._mask_secrets(kwargs)
        if error:
            data.update({"error_type": type(error).__name__, "error_message": str(error)})
        self.logger.error(message, **data)
