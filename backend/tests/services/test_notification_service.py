"""Tests for the log-only maintenance notification transport."""

import logging
from uuid import uuid4

import pytest

from app.models.maintenance import MaintenancePriority, MaintenanceRequest, MaintenanceStatus
from app.models.user import User, UserRole
from app.services import notification_service


def _request() -> MaintenanceRequest:
    return MaintenanceRequest(
        id=uuid4(),
        unit_id=uuid4(),
        reported_by=uuid4(),
        title="Leaking faucet",
        description="The kitchen faucet is dripping continuously.",
        priority=MaintenancePriority.MEDIUM,
        status=MaintenanceStatus.OPEN,
    )


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value}@example.com",
        hashed_password="hashed",
        full_name=role.value.title(),
        role=role,
        is_active=True,
    )


def test_submitted_notification_logs_recipient_context(caplog: pytest.LogCaptureFixture) -> None:
    request = _request()
    owner = _user(UserRole.LANDLORD)

    with caplog.at_level(logging.INFO, logger=notification_service.__name__):
        notification_service.notify_maintenance_submitted(request=request, recipient=owner)

    [record] = caplog.records
    assert record.levelno == logging.INFO
    assert record.context == {
        "event": "maintenance_request_submitted",
        "transport": "log_only",
        "maintenance_request_id": str(request.id),
        "unit_id": str(request.unit_id),
        "recipient_id": str(owner.id),
        "recipient_role": "landlord",
    }


def test_resolved_notification_without_recipient_warns(caplog: pytest.LogCaptureFixture) -> None:
    request = _request()

    with caplog.at_level(logging.INFO, logger=notification_service.__name__):
        notification_service.notify_maintenance_resolved(request=request, recipient=None)

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.context["event"] == "maintenance_request_resolved"
    assert record.context["recipient_id"] is None
