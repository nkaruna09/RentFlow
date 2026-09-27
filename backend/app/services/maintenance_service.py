"""Work-order assignment and status-transition rules."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationError
from app.models.maintenance import MaintenanceRequest, MaintenanceStatus
from app.repositories import maintenance as maintenance_repository

INVALID_TRANSITION_CODE = "invalid_maintenance_status_transition"
_UNSET = object()

VALID_STATUS_TRANSITIONS: Mapping[MaintenanceStatus, frozenset[MaintenanceStatus]] = {
    MaintenanceStatus.OPEN: frozenset({MaintenanceStatus.ASSIGNED}),
    MaintenanceStatus.ASSIGNED: frozenset({MaintenanceStatus.IN_PROGRESS}),
    MaintenanceStatus.IN_PROGRESS: frozenset({MaintenanceStatus.RESOLVED}),
    MaintenanceStatus.RESOLVED: frozenset({MaintenanceStatus.CLOSED, MaintenanceStatus.OPEN}),
    MaintenanceStatus.CLOSED: frozenset({MaintenanceStatus.OPEN}),
}


def _invalid_transition(current: MaintenanceStatus, target: MaintenanceStatus) -> ConflictError:
    return ConflictError(
        f"Invalid maintenance status transition from '{current.value}' to '{target.value}'",
        code=INVALID_TRANSITION_CODE,
    )


def validate_status_transition(current: MaintenanceStatus, target: MaintenanceStatus) -> None:
    """Reject status changes that skip or reverse the maintenance workflow."""
    if target == current:
        return
    if target not in VALID_STATUS_TRANSITIONS[current]:
        raise _invalid_transition(current, target)


def transition_status(
    request: MaintenanceRequest,
    target: MaintenanceStatus,
    *,
    transitioned_at: datetime | None = None,
) -> MaintenanceRequest:
    """Apply one valid status transition to an in-memory request."""
    validate_status_transition(request.status, target)
    if target == request.status:
        return request

    request.status = target
    if target == MaintenanceStatus.RESOLVED:
        request.resolved_at = transitioned_at or datetime.now(UTC)
    elif target == MaintenanceStatus.OPEN:
        request.resolved_at = None
        request.assigned_to = None
    return request


def assign_request(
    request: MaintenanceRequest,
    assigned_to: uuid.UUID,
) -> MaintenanceRequest:
    """Assign an open request, automatically moving it to ``assigned``."""
    if not isinstance(assigned_to, uuid.UUID):
        raise ValidationError("assigned_to must be a valid user ID")
    if request.status not in {MaintenanceStatus.OPEN, MaintenanceStatus.ASSIGNED}:
        raise _invalid_transition(request.status, MaintenanceStatus.ASSIGNED)

    request.assigned_to = assigned_to
    if request.status == MaintenanceStatus.OPEN:
        transition_status(request, MaintenanceStatus.ASSIGNED)
    return request


def reopen_request(request: MaintenanceRequest) -> MaintenanceRequest:
    """Return a resolved or closed request to the unassigned open queue."""
    return transition_status(request, MaintenanceStatus.OPEN)


async def update_request(
    db: AsyncSession,
    request: MaintenanceRequest,
    values: Mapping[str, object],
    *,
    transitioned_at: datetime | None = None,
) -> MaintenanceRequest:
    """Apply assignment/workflow changes and persist the request atomically."""
    updates = dict(values)
    assigned_to = updates.pop("assigned_to", _UNSET)
    requested_status = updates.pop("status", _UNSET)

    planned_status = request.status
    if assigned_to is not _UNSET and assigned_to is not None:
        if not isinstance(assigned_to, uuid.UUID):
            raise ValidationError("assigned_to must be a valid user ID")
        if planned_status not in {MaintenanceStatus.OPEN, MaintenanceStatus.ASSIGNED}:
            raise _invalid_transition(planned_status, MaintenanceStatus.ASSIGNED)
        planned_status = MaintenanceStatus.ASSIGNED

    if requested_status is not _UNSET:
        if not isinstance(requested_status, MaintenanceStatus):
            raise ValidationError("status must be a valid maintenance status")
        validate_status_transition(planned_status, requested_status)

    if (
        assigned_to is None
        and request.status != MaintenanceStatus.OPEN
        and requested_status != MaintenanceStatus.OPEN
    ):
        raise ConflictError("An assignment can only be cleared when reopening the request")

    if isinstance(assigned_to, uuid.UUID):
        assign_request(request, assigned_to)
    elif assigned_to is None:
        request.assigned_to = None

    if isinstance(requested_status, MaintenanceStatus):
        transition_status(request, requested_status, transitioned_at=transitioned_at)

    for field, value in updates.items():
        setattr(request, field, value)
    return await maintenance_repository.update(db, request)


__all__ = [
    "INVALID_TRANSITION_CODE",
    "VALID_STATUS_TRANSITIONS",
    "assign_request",
    "reopen_request",
    "transition_status",
    "update_request",
    "validate_status_transition",
]
