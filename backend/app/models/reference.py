"""Reference data models: ATC classes, medications, geography, actors, users."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.dbtypes import JSONType
from app.core.enums import PharmacyType, Role, SupplierType


class AtcClass(Base, TimestampMixin):
    __tablename__ = "atc_classes"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    label_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    label_ar: Mapped[str | None] = mapped_column(String(255))
    parent_code: Mapped[str | None] = mapped_column(ForeignKey("atc_classes.code"))


class Medication(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "medications"

    # Full ATC level-5 code (e.g. J01CA04). Not FK-constrained: ATC is an external
    # WHO taxonomy; atc_classes holds curated labels for the levels we display.
    atc_code: Mapped[str] = mapped_column(String(8), nullable=False)
    dci: Mapped[str] = mapped_column(String(255), nullable=False)  # Dénomination Commune Internationale
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    form: Mapped[str] = mapped_column(String(80), nullable=False)  # comprimé, sirop, injectable...
    dosage: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="boîte")
    ddd_value: Mapped[float | None] = mapped_column(Numeric(10, 3))
    ddd_unit: Mapped[str | None] = mapped_column(String(20))
    unit_price_tnd: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_medications_atc_code", "atc_code"),
        # Trigram GIN indexes are added for PostgreSQL by the migration; plain
        # name indexes keep search reasonable on any dialect.
        Index("ix_medications_brand_name", "brand_name"),
    )


class Governorate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "governorates"

    code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    name_fr: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    centroid_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    # GeoJSON polygon (portable). PostGIS geometry is a production optimization.
    geojson: Mapped[dict | None] = mapped_column(JSONType)


class Pharmacy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pharmacies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[PharmacyType] = mapped_column(Enum(PharmacyType, name="pharmacy_type"),
                                               nullable=False)
    governorate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("governorates.id"), nullable=False
    )
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(40))
    on_call: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    governorate: Mapped[Governorate] = relationship()

    __table_args__ = (Index("ix_pharmacies_governorate_id", "governorate_id"),)


class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Tunisie")
    type: Mapped[SupplierType] = mapped_column(Enum(SupplierType, name="supplier_type"),
                                               nullable=False)
    reliability_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.9)
    avg_lead_time_days: Mapped[int] = mapped_column(Integer, default=21)


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    keycloak_sub: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), nullable=False)
    pharmacy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pharmacies.id"))
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("suppliers.id"))
