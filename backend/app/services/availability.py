"""Availability status derivation shared by citizen and pharmacy views."""
from __future__ import annotations

from app.core.enums import AvailabilityStatus, Severity

# Map a shortage severity to a citizen-facing availability status.
_SEVERITY_TO_AVAILABILITY = {
    Severity.green: AvailabilityStatus.available,
    Severity.yellow: AvailabilityStatus.available,
    Severity.orange: AvailabilityStatus.tension,
    Severity.red: AvailabilityStatus.tension,
    Severity.critical: AvailabilityStatus.shortage,
}


def availability_from_severity(severity: Severity | None) -> AvailabilityStatus:
    if severity is None:
        return AvailabilityStatus.available
    return _SEVERITY_TO_AVAILABILITY[severity]


def availability_from_stock(quantity: int, min_threshold: int) -> AvailabilityStatus:
    if quantity <= 0:
        return AvailabilityStatus.shortage
    if quantity <= max(min_threshold, 1):
        return AvailabilityStatus.tension
    return AvailabilityStatus.available
