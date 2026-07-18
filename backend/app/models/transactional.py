"""Transactional models: stock, sales, orders, imports, distribution, signals."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.dbtypes import JSONType
from app.core.enums import ImportOrderStatus, OrderStatus, ReservationStatus, SignalType


class StockLevel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "stock_levels"

    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pharmacies.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("pharmacy_id", "medication_id", "recorded_at",
                         name="uq_stock_pharmacy_med_date"),
        Index("ix_stock_med_date", "medication_id", "recorded_at"),
    )


class NationalStock(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "national_stock"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warehouse: Mapped[str] = mapped_column(String(120), default="PCT Tunis")
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("medication_id", "warehouse", "recorded_at",
                         name="uq_national_stock_med_wh_date"),
        Index("ix_national_stock_med_date", "medication_id", "recorded_at"),
    )


class SalesDaily(Base, UUIDMixin):
    __tablename__ = "sales_daily"

    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pharmacies.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_tnd: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    stockout: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint("pharmacy_id", "medication_id", "date",
                         name="uq_sales_pharmacy_med_date"),
        Index("ix_sales_med_date", "medication_id", "date"),
        Index("ix_sales_pharmacy_date", "pharmacy_id", "date"),
    )


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pharmacies.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"),
                                                default=OrderStatus.pending)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderItem(Base, UUIDMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    qty_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_delivered: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_order_items_order_id", "order_id"),)


class Reservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reservations"

    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pharmacies.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    citizen_contact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"), default=ReservationStatus.active
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Return(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "returns"

    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pharmacies.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, nullable=False)


class ImportOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "import_orders"

    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ordered_at: Mapped[date] = mapped_column(Date, nullable=False)
    promised_at: Mapped[date] = mapped_column(Date, nullable=False)
    arrived_at: Mapped[date | None] = mapped_column(Date)
    port: Mapped[str | None] = mapped_column(String(80), default="Radès")
    status: Mapped[ImportOrderStatus] = mapped_column(
        Enum(ImportOrderStatus, name="import_order_status"), default=ImportOrderStatus.ordered
    )

    __table_args__ = (Index("ix_import_orders_med", "medication_id"),)


class Shipment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shipments"

    import_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("import_orders.id"), nullable=False
    )
    promised_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_date: Mapped[date | None] = mapped_column(Date)
    # Positive when the shipment arrived later than promised. Computed at write
    # time (portable across dialects; no DB generated column).
    delay_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="in_transit")


class DistributionRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "distribution_records"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    governorate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("governorates.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    shipped_at: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (Index("ix_distribution_med_gov", "medication_id", "governorate_id"),)


class ShortageHistory(Base, UUIDMixin, TimestampMixin):
    """Ground-truth record of a past shortage episode (labels for the classifier)."""

    __tablename__ = "shortages_history"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date)
    severity: Mapped[str] = mapped_column(String(20), default="red")
    cause: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (Index("ix_shortage_hist_med", "medication_id", "started_at"),)


class ExternalSignal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "external_signals"

    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType, name="signal_type"),
                                                    nullable=False)
    region: Mapped[str | None] = mapped_column(String(120))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    source: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_external_signals_type_date", "signal_type", "date"),)
