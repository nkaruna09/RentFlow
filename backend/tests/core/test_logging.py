"""Tests for the Application Insights wiring in app.core.logging."""

import logging
from unittest.mock import patch

import pytest

from app.core import logging as app_logging
from app.core.config import Settings


@pytest.fixture(autouse=True)
def _reset_monitoring_flag():
    app_logging._monitoring_configured = False
    yield
    app_logging._monitoring_configured = False


def test_monitoring_is_a_noop_without_a_connection_string() -> None:
    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as configure:
        assert (
            app_logging.configure_monitoring(Settings(applicationinsights_connection_string=None))
            is False
        )
    configure.assert_not_called()


def test_monitoring_exports_the_app_logger_once() -> None:
    settings = Settings(
        environment="staging",
        secret_key="test-secret",
        applicationinsights_connection_string="InstrumentationKey=00000000-0000-0000-0000-000000000000",
    )
    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as configure:
        assert app_logging.configure_monitoring(settings) is True
        assert app_logging.configure_monitoring(settings) is True

    configure.assert_called_once()
    kwargs = configure.call_args.kwargs
    assert kwargs["connection_string"] == settings.applicationinsights_connection_string
    assert kwargs["logger_name"] == "app"
    assert kwargs["resource_attributes"]["deployment.environment"] == "staging"


def test_setup_logging_returns_the_exported_app_logger() -> None:
    logger = app_logging.setup_logging(Settings(applicationinsights_connection_string=None))
    assert logger.name == "app"
    assert isinstance(logging.getLogger().handlers[0].formatter, app_logging.JsonFormatter)
