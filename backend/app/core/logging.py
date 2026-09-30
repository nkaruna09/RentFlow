"""Structured logging config wired to Azure Application Insights.

Logs always go to stdout as JSON (Container Apps ships stdout to Log Analytics).
When ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is set, logs under the ``app``
namespace plus request/dependency traces are also exported to Application
Insights via the Azure Monitor OpenTelemetry distro. Locally it is unset, so
monitoring is a no-op.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings

APP_LOGGER_NAME = "app"
_monitoring_configured = False


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

    configure_monitoring(resolved_settings)
    return logging.getLogger(APP_LOGGER_NAME)


def configure_monitoring(settings: Settings) -> bool:
    """Export ``app.*`` logs and traces to Application Insights, once per process.

    The exporter is attached to the ``app`` logger rather than the root logger so
    ``setup_logging`` clearing root handlers never silently detaches it, and so
    third-party debug chatter is not billed as App Insights ingestion.
    """
    global _monitoring_configured
    connection_string = settings.applicationinsights_connection_string
    if not connection_string or _monitoring_configured:
        return _monitoring_configured

    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(
        connection_string=connection_string,
        logger_name=APP_LOGGER_NAME,
        resource_attributes={
            "service.name": "rentflow-api",
            "deployment.environment": settings.environment,
        },
    )
    _monitoring_configured = True
    return True
