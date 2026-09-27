"""Tests for maintenance assignment and lifecycle rules."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError
from app.models.maintenance import MaintenancePriority, MaintenanceRequest, MaintenanceStatus
from app.repositories import maintenance as maintenance_repository
from app.services.maintenance_service import (
    INVALID_TRANSITION_CODE,
    assign_request,
    reopen_request,
    transition_status,
    update_request,
)


def _request(*, status: MaintenanceStatus = MaintenanceStatus.OPEN) -> MaintenanceRequest:
    return MaintenanceRequest(
        id=uuid4(),
        unit_id=uuid4(),
        reported_by=uuid4(),
        title="Leaking faucet",
        description="The kitchen faucet is dripping continuously.",
        priority=MaintenancePriority.MEDIUM,
        status=status,
    )


def test_request_can_follow_the_complete_status_graph() -> None:
    request = _request()
    resolved_at = datetime(2026, 9, 27, 12, tzinfo=UTC)

    transition_status(request, MaintenanceStatus.ASSIGNED)
    transition_status(request, MaintenanceStatus.IN_PROGRESS)
    transition_status(request, MaintenanceStatus.RESOLVED, transitioned_at=resolved_at)

    assert request.status is MaintenanceStatus.RESOLVED
    assert request.resolved_at == resolved_at

    transition_status(request, MaintenanceStatus.CLOSED)

    assert request.status is MaintenanceStatus.CLOSED
    assert request.resolved_at == resolved_at


def test_invalid_transition_is_clear_and_does_not_mutate_request() -> None:
    request = _request()

    with pytest.raises(ConflictError) as error:
        transition_status(request, MaintenanceStatus.CLOSED)

    assert error.value.detail == "Invalid maintenance status transition from 'open' to 'closed'"
    assert error.value.code == INVALID_TRANSITION_CODE
    assert request.status is MaintenanceStatus.OPEN
    assert request.resolved_at is None


def test_assignment_moves_an_open_request_to_assigned() -> None:
    request = _request()
    assignee_id = uuid4()

    assign_request(request, assignee_id)

    assert request.assigned_to == assignee_id
    assert request.status is MaintenanceStatus.ASSIGNED


@pytest.mark.parametrize("status", [MaintenanceStatus.RESOLVED, MaintenanceStatus.CLOSED])
def test_reopen_returns_terminal_requests_to_unassigned_open_queue(
    status: MaintenanceStatus,
) -> None:
    request = _request(status=status)
    request.assigned_to = uuid4()
    request.resolved_at = datetime(2026, 9, 27, 12, tzinfo=UTC)

    reopen_request(request)

    assert request.status is MaintenanceStatus.OPEN
    assert request.assigned_to is None
    assert request.resolved_at is None


async def test_update_can_assign_and_start_work_atomically() -> None:
    request = _request()
    assignee_id = uuid4()
    db = AsyncMock()

    with patch.object(
        maintenance_repository,
        "update",
        AsyncMock(side_effect=lambda _db, entity: entity),
    ) as update_mock:
        updated = await update_request(
            db,
            request,
            {
                "assigned_to": assignee_id,
                "status": MaintenanceStatus.IN_PROGRESS,
                "priority": MaintenancePriority.HIGH,
            },
        )

    assert updated is request
    assert request.assigned_to == assignee_id
    assert request.status is MaintenanceStatus.IN_PROGRESS
    assert request.priority is MaintenancePriority.HIGH
    update_mock.assert_awaited_once_with(db, request)


async def test_invalid_combined_update_is_not_partially_applied() -> None:
    request = _request()

    with (
        patch.object(maintenance_repository, "update", AsyncMock()) as update_mock,
        pytest.raises(ConflictError, match="assigned.*closed"),
    ):
        await update_request(
            AsyncMock(),
            request,
            {"assigned_to": uuid4(), "status": MaintenanceStatus.CLOSED},
        )

    assert request.status is MaintenanceStatus.OPEN
    assert request.assigned_to is None
    update_mock.assert_not_awaited()
