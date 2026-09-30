"""Notification events awaiting Azure Communication Services delivery.

M7 will replace the current structured-log transport with email/SMS delivery.
Keeping the domain-specific functions here lets callers emit notifications now
without coupling maintenance workflows to the eventual Azure SDK.
"""

from __future__ import annotations

import logging

from app.models.maintenance import MaintenanceRequest
from app.models.user import User

logger = logging.getLogger(__name__)


def _emit_log_notification(
    *,
    event: str,
    request: MaintenanceRequest,
    recipient: User | None,
) -> None:
    context = {
        "event": event,
        "transport": "log_only",
        "maintenance_request_id": str(request.id),
        "unit_id": str(request.unit_id),
        "recipient_id": str(recipient.id) if recipient else None,
        "recipient_role": recipient.role.value if recipient else None,
    }
    if recipient is None:
        logger.warning(
            "Maintenance notification has no eligible recipient",
            extra={"context": context},
        )
        return
    logger.info("Maintenance notification emitted", extra={"context": context})


def notify_maintenance_submitted(*, request: MaintenanceRequest, recipient: User | None) -> None:
    """Notify the property owner that a maintenance request was submitted."""
    _emit_log_notification(
        event="maintenance_request_submitted",
        request=request,
        recipient=recipient,
    )


def notify_maintenance_resolved(*, request: MaintenanceRequest, recipient: User | None) -> None:
    """Notify the active tenant that their maintenance request was resolved."""
    _emit_log_notification(
        event="maintenance_request_resolved",
        request=request,
        recipient=recipient,
    )


__all__ = ["notify_maintenance_resolved", "notify_maintenance_submitted"]
