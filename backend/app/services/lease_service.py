"""Lease lifecycle rules: overlap checks, activation, renewal, and termination."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.lease import Lease, LeaseStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories import lease as lease_repository
from app.repositories import unit as unit_repository

OVERLAP_DETAIL = "Lease overlaps an active lease for this unit"


def _raise_overlap(exc: IntegrityError) -> None:
    raise ConflictError(OVERLAP_DETAIL, code="lease_overlap") from exc


def _validate_dates(start_date: date, end_date: date) -> None:
    if end_date <= start_date:
        raise ValidationError("Lease end_date must be after start_date")


async def list_leases(
    db: AsyncSession,
    current_user: User,
    *,
    unit_id: uuid.UUID | None,
    tenant_id: uuid.UUID | None,
    status: LeaseStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Lease], int]:
    return await lease_repository.list_visible(
        db,
        current_user.id,
        current_user.role,
        unit_id=unit_id,
        tenant_id=tenant_id,
        lease_status=status,
        page=page,
        page_size=page_size,
    )


async def _get_for_manager(db: AsyncSession, lease_id: uuid.UUID, current_user: User) -> Lease:
    lease = await lease_repository.get_visible(db, lease_id, current_user.id, current_user.role)
    if lease is None:
        raise NotFoundError("Lease not found")
    return lease


async def create_lease(db: AsyncSession, current_user: User, values: dict[str, object]) -> Lease:
    unit_id = values["unit_id"]
    tenant_id = values["tenant_id"]
    if (
        not isinstance(unit_id, uuid.UUID)
        or await unit_repository.get_for_owner(db, unit_id, current_user.id) is None
    ):
        raise NotFoundError("Unit not found")
    if not isinstance(tenant_id, uuid.UUID) or await db.get(Tenant, tenant_id) is None:
        raise NotFoundError("Tenant not found")
    start_date = values["start_date"]
    end_date = values["end_date"]
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValidationError("Lease dates are invalid")
    _validate_dates(start_date, end_date)
    requested_status = values.get("status", LeaseStatus.DRAFT)
    if requested_status not in {LeaseStatus.DRAFT, LeaseStatus.ACTIVE}:
        raise ValidationError("New leases must be draft or active")
    try:
        return await lease_repository.create(db, values)
    except IntegrityError as exc:
        await db.rollback()
        _raise_overlap(exc)
    raise AssertionError("unreachable")


async def get_lease(db: AsyncSession, lease_id: uuid.UUID, current_user: User) -> Lease:
    lease = await lease_repository.get_visible(db, lease_id, current_user.id, current_user.role)
    if lease is None:
        raise NotFoundError("Lease not found")
    return lease


async def update_lease(
    db: AsyncSession,
    lease_id: uuid.UUID,
    current_user: User,
    values: dict[str, object],
) -> Lease:
    lease = await _get_for_manager(db, lease_id, current_user)
    if lease.status != LeaseStatus.DRAFT:
        raise ConflictError("Only draft leases can be updated")
    start_date = values.get("start_date", lease.start_date)
    end_date = values.get("end_date", lease.end_date)
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValidationError("Lease dates are invalid")
    _validate_dates(start_date, end_date)
    try:
        return await lease_repository.update(db, lease, values)
    except IntegrityError as exc:
        await db.rollback()
        _raise_overlap(exc)
    raise AssertionError("unreachable")


async def activate_lease(db: AsyncSession, lease_id: uuid.UUID, current_user: User) -> Lease:
    lease = await _get_for_manager(db, lease_id, current_user)
    if lease.status != LeaseStatus.DRAFT:
        raise ConflictError("Only draft leases can be activated")
    try:
        return await lease_repository.update(db, lease, {"status": LeaseStatus.ACTIVE})
    except IntegrityError as exc:
        await db.rollback()
        _raise_overlap(exc)
    raise AssertionError("unreachable")


async def renew_lease(
    db: AsyncSession,
    lease_id: uuid.UUID,
    current_user: User,
    values: dict[str, object],
) -> Lease:
    lease = await _get_for_manager(db, lease_id, current_user)
    if lease.status not in {LeaseStatus.ACTIVE, LeaseStatus.EXPIRED}:
        raise ConflictError("Only active or expired leases can be renewed")
    duration = lease.end_date - lease.start_date
    start_date = values.get("start_date", lease.end_date)
    if not isinstance(start_date, date):
        raise ValidationError("Lease dates are invalid")
    end_date = values.get("end_date", start_date + duration)
    if not isinstance(end_date, date):
        raise ValidationError("Lease dates are invalid")
    _validate_dates(start_date, end_date)
    successor_values: dict[str, object] = {
        "unit_id": lease.unit_id,
        "tenant_id": lease.tenant_id,
        "start_date": start_date,
        "end_date": end_date,
        "rent_amount": values.get("rent_amount", lease.rent_amount),
        "deposit_amount": values.get("deposit_amount", lease.deposit_amount),
        "billing_day": values.get("billing_day", lease.billing_day),
        "status": LeaseStatus.DRAFT,
    }
    try:
        return await lease_repository.create(db, successor_values)
    except IntegrityError as exc:
        await db.rollback()
        _raise_overlap(exc)
    raise AssertionError("unreachable")


async def terminate_lease(
    db: AsyncSession,
    lease_id: uuid.UUID,
    current_user: User,
    *,
    reason: str,
    end_date: date,
) -> Lease:
    if not reason.strip():
        raise ValidationError("Termination reason is required")
    lease = await _get_for_manager(db, lease_id, current_user)
    if lease.status != LeaseStatus.ACTIVE:
        raise ConflictError("Only active leases can be terminated")
    _validate_dates(lease.start_date, end_date)
    if end_date >= lease.end_date:
        raise ValidationError("Termination end_date must be before the lease end_date")
    return await lease_repository.update(
        db, lease, {"end_date": end_date, "status": LeaseStatus.TERMINATED}
    )


__all__ = [
    "activate_lease",
    "create_lease",
    "get_lease",
    "list_leases",
    "renew_lease",
    "terminate_lease",
    "update_lease",
]
