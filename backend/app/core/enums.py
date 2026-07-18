"""Domain enumerations shared across models, schemas, and services."""
from __future__ import annotations

import enum


class Role(str, enum.Enum):
    pct_admin = "pct_admin"
    regional_authority = "regional_authority"
    hospital_pharmacist = "hospital_pharmacist"
    community_pharmacist = "community_pharmacist"
    supplier = "supplier"
    citizen = "citizen"


class PharmacyType(str, enum.Enum):
    community = "community"
    hospital = "hospital"


class SupplierType(str, enum.Enum):
    local_manufacturer = "local_manufacturer"
    importer = "importer"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class ImportOrderStatus(str, enum.Enum):
    ordered = "ordered"
    in_transit = "in_transit"
    at_port = "at_port"
    cleared = "cleared"
    arrived = "arrived"
    delayed = "delayed"


class ReservationStatus(str, enum.Enum):
    active = "active"
    fulfilled = "fulfilled"
    expired = "expired"
    cancelled = "cancelled"


class SignalType(str, enum.Enum):
    weather = "weather"
    epidemiological = "epidemiological"
    who_alert = "who_alert"
    ministry = "ministry"
    economic = "economic"
    logistics = "logistics"


class Trend(str, enum.Enum):
    rising = "rising"
    stable = "stable"
    falling = "falling"


class Severity(str, enum.Enum):
    """Shortage risk levels — ordered from lowest to highest."""

    green = "green"
    yellow = "yellow"
    orange = "orange"
    red = "red"
    critical = "critical"

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK[self]

    # Severity inherits from str, whose comparison operators order alphabetically
    # ("critical" < "orange"), which is wrong. Define all four to order by rank.
    def __ge__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, Severity):
            return self.rank >= other.rank
        return NotImplemented

    def __gt__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, Severity):
            return self.rank > other.rank
        return NotImplemented

    def __le__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, Severity):
            return self.rank <= other.rank
        return NotImplemented

    def __lt__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, Severity):
            return self.rank < other.rank
        return NotImplemented


_SEVERITY_RANK = {
    Severity.green: 0,
    Severity.yellow: 1,
    Severity.orange: 2,
    Severity.red: 3,
    Severity.critical: 4,
}


class RecommendationType(str, enum.Enum):
    increase_import = "increase_import"
    redistribute = "redistribute"
    prioritize_hospitals = "prioritize_hospitals"
    emergency_procurement = "emergency_procurement"
    adjust_order = "adjust_order"


class RecommendationStatus(str, enum.Enum):
    proposed = "proposed"
    validated = "validated"
    rejected = "rejected"


class EquivalenceLevel(str, enum.Enum):
    identical_dci = "identical_dci"
    same_atc5 = "same_atc5"
    same_atc4 = "same_atc4"
    same_atc3 = "same_atc3"


class AlertScope(str, enum.Enum):
    national = "national"
    governorate = "governorate"
    pharmacy = "pharmacy"


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"


class AvailabilityStatus(str, enum.Enum):
    available = "available"       # Disponible
    tension = "tension"           # Tension d'approvisionnement
    shortage = "shortage"         # Rupture
