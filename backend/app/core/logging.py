"""Structured logging config wired to Azure Application Insights."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings


class JsonFormatter(logging.Formatter):
    """Render log records as JSON for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "context") and record.context:
            payload["context"] = record.context
        return json.dumps(payload, default=str)


def setup_logging(settings: Settings | None = None) -> logging.Logger:
    """Configure the root logger with structured JSON output."""

    resolved_settings = settings or get_settings()
    level_name = str(resolved_settings.log_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    return root_logger
