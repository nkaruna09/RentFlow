"""Unit tests for payment reconciliation business rules."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.payment import Invoice, InvoiceStatus, Payment, PaymentMethod
from app.models.user import User, UserRole
from app.repositories import payment as payment_repository
from app.services.payment_service import create_invoice, record_payment


def _user() -> User:
    return User(
        id=uuid4(),
        email="owner@example.com",
        hashed_password="hashed",
        full_name="Owner",
        role=UserRole.LANDLORD,
        is_active=True,
    )


def _invoice(*, status: InvoiceStatus = InvoiceStatus.OPEN) -> Invoice:
    return Invoice(
        id=uuid4(),
        lease_id=uuid4(),
        period_start=date(2026, 9, 1),
        period_end=date(2026, 10, 1),
        amount_due=Decimal("100.00"),
        due_date=date(2026, 9, 1),
        status=status,
    )


def _payment_values(amount: str) -> dict[str, object]:
    return {
        "amount": Decimal(amount),
        "paid_at": datetime(2026, 9, 27, 12, tzinfo=UTC),
        "method": PaymentMethod.BANK_TRANSFER,
        "reference": None,
    }


async def _return_payment(_db, payment: Payment, _invoice: Invoice) -> Payment:
    return payment


@pytest.mark.parametrize(
    ("already_paid", "payment", "expected_status"),
    [
        ("0.00", "40.00", InvoiceStatus.PARTIAL),
        ("40.00", "60.00", InvoiceStatus.PAID),
    ],
)
async def test_record_payment_reconciles_cumulative_amounts(
    already_paid: str,
    payment: str,
    expected_status: InvoiceStatus,
) -> None:
    invoice = _invoice(status=InvoiceStatus.OVERDUE)
    with (
        patch.object(
            payment_repository,
            "get_for_owner",
            AsyncMock(return_value=invoice),
        ),
        patch.object(
            payment_repository,
            "total_paid",
            AsyncMock(return_value=Decimal(already_paid)),
        ),
        patch.object(
            payment_repository,
            "create_payment",
            AsyncMock(side_effect=_return_payment),
        ) as create_payment_mock,
    ):
        recorded = await record_payment(AsyncMock(), invoice.id, _user(), _payment_values(payment))

    assert invoice.status is expected_status
    assert recorded.invoice_id == invoice.id
    assert recorded.amount == Decimal(payment)
    create_payment_mock.assert_awaited_once()


async def test_record_payment_rejects_overpayment() -> None:
    invoice = _invoice()
    with (
        patch.object(
            payment_repository,
            "get_for_owner",
            AsyncMock(return_value=invoice),
        ),
        patch.object(
            payment_repository,
            "total_paid",
            AsyncMock(return_value=Decimal("90.00")),
        ),
        pytest.raises(ValidationError, match="exceeds"),
    ):
        await record_payment(AsyncMock(), invoice.id, _user(), _payment_values("10.01"))


async def test_record_payment_rejects_void_invoice() -> None:
    invoice = _invoice(status=InvoiceStatus.VOID)
    with (
        patch.object(
            payment_repository,
            "get_for_owner",
            AsyncMock(return_value=invoice),
        ),
        pytest.raises(ConflictError, match="void invoice"),
    ):
        await record_payment(AsyncMock(), invoice.id, _user(), _payment_values("10.00"))


async def test_record_payment_hides_an_inaccessible_invoice() -> None:
    with (
        patch.object(
            payment_repository,
            "get_for_owner",
            AsyncMock(return_value=None),
        ),
        pytest.raises(NotFoundError, match="Invoice not found"),
    ):
        await record_payment(AsyncMock(), uuid4(), _user(), _payment_values("10.00"))


async def test_create_invoice_forces_open_status() -> None:
    invoice = _invoice(status=InvoiceStatus.OPEN)
    values: dict[str, object] = {
        "lease_id": invoice.lease_id,
        "period_start": invoice.period_start,
        "period_end": invoice.period_end,
        "amount_due": invoice.amount_due,
        "due_date": invoice.due_date,
        "status": InvoiceStatus.PAID,
    }
    with (
        patch(
            "app.services.payment_service.lease_repository.get_visible",
            AsyncMock(return_value=object()),
        ),
        patch.object(
            payment_repository,
            "create_invoice",
            AsyncMock(return_value=invoice),
        ) as create_invoice_mock,
    ):
        created = await create_invoice(AsyncMock(), _user(), values)

    assert created is invoice
    assert values["status"] is InvoiceStatus.OPEN
    create_invoice_mock.assert_awaited_once()
