"""Work-order assignment and status-transition rules."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.maintenance import (
    MaintenanceComment,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.user import User
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


async def list_requests(
    db: AsyncSession,
    current_user: User,
    *,
    unit_id: uuid.UUID | None,
    status: MaintenanceStatus | None,
    priority: MaintenancePriority | None,
    page: int,
    page_size: int,
) -> tuple[list[MaintenanceRequest], int]:
    """List requests visible through the caller's properties or active lease."""
    return await maintenance_repository.list_visible(
        db,
        current_user.id,
        current_user.role,
        unit_id=unit_id,
        request_status=status,
        priority=priority,
        page=page,
        page_size=page_size,
    )


async def create_request(
    db: AsyncSession,
    current_user: User,
    values: dict[str, object],
) -> MaintenanceRequest:
    """Create an open request for a unit the caller may access."""
    unit_id = values.get("unit_id")
    if not isinstance(unit_id, uuid.UUID) or not await maintenance_repository.can_access_unit(
        db, unit_id, current_user.id, current_user.role
    ):
        raise NotFoundError("Unit not found")
    return await maintenance_repository.create(
        db,
        {
            **values,
            "reported_by": current_user.id,
            "status": MaintenanceStatus.OPEN,
            "assigned_to": None,
            "resolved_at": None,
        },
    )


async def get_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    current_user: User,
    *,
    for_update: bool = False,
) -> MaintenanceRequest:
    """Return a visible request without disclosing inaccessible IDs."""
    request = await maintenance_repository.get_visible(
        db,
        request_id,
        current_user.id,
        current_user.role,
        for_update=for_update,
    )
    if request is None:
        raise NotFoundError("Maintenance request not found")
    return request


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


async def update_visible_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    current_user: User,
    values: Mapping[str, object],
) -> MaintenanceRequest:
    """Update a manager-visible request while enforcing workflow rules."""
    request = await get_request(db, request_id, current_user, for_update=True)
    assigned_to = values.get("assigned_to", _UNSET)
    if isinstance(assigned_to, uuid.UUID) and await db.get(User, assigned_to) is None:
        raise NotFoundError("Assignee not found")
    return await update_request(db, request, values)


async def add_comment(
    db: AsyncSession,
    request_id: uuid.UUID,
    current_user: User,
    *,
    body: str,
) -> MaintenanceComment:
    """Append a comment when the caller can see the parent request."""
    await get_request(db, request_id, current_user)
    if not body.strip():
        raise ValidationError("Comment body is required")
    return await maintenance_repository.create_comment(
        db,
        request_id=request_id,
        author_id=current_user.id,
        body=body,
    )


__all__ = [
    "INVALID_TRANSITION_CODE",
    "VALID_STATUS_TRANSITIONS",
    "add_comment",
    "assign_request",
    "create_request",
    "get_request",
    "list_requests",
    "reopen_request",
    "transition_status",
    "update_request",
    "update_visible_request",
    "validate_status_transition",
]
