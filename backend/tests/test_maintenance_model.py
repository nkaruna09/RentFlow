"""Maintenance model, relationship, and schema tests."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance import (
    MaintenanceComment,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.property import Property, PropertyType
from app.models.unit import Unit, UnitStatus
from app.schemas.maintenance import MaintenanceCommentCreate, MaintenanceRequestCreate


async def test_maintenance_request_and_comment_persist(db_session: AsyncSession, make_user) -> None:
    reporter = await make_user()
    assignee = await make_user()
    property_ = Property(
        owner_id=reporter.id,
        name="Maintenance property",
        address_line1="8 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M8",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 8",
        bedrooms=Decimal("1"),
        bathrooms=Decimal("1"),
        market_rent=Decimal("1200.00"),
        status=UnitStatus.OCCUPIED,
    )
    request = MaintenanceRequest(
        unit=unit,
        reporter=reporter,
        assignee=assignee,
        title="Leaking faucet",
        description="The kitchen faucet is dripping continuously.",
        priority=MaintenancePriority.MEDIUM,
    )
    comment = MaintenanceComment(
        request=request,
        author=assignee,
        body="A plumber has been scheduled.",
    )
    db_session.add_all([property_, request, comment])

    await db_session.flush()
    await db_session.refresh(request)
    await db_session.refresh(comment)

    assert request.status is MaintenanceStatus.OPEN
    assert request.reported_by == reporter.id
    assert request.assigned_to == assignee.id
    assert comment.request_id == request.id
    assert comment.author_id == assignee.id
    assert request.created_at is not None
    assert comment.created_at is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [("title", ""), ("description", "")],
)
def test_maintenance_request_schema_rejects_empty_text(field: str, value: str) -> None:
    values = {
        "unit_id": "11111111-1111-1111-1111-111111111111",
        "title": "Leaking faucet",
        "description": "The kitchen faucet is dripping.",
        "priority": "high",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        MaintenanceRequestCreate.model_validate(values)


def test_maintenance_comment_schema_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        MaintenanceCommentCreate(body="")
