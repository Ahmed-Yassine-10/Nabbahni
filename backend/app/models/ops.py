"""Operational models: alerts, notifications, audit logs."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.enums import AlertScope, NotificationChannel, Severity


class Alert(Base, UUIDMixin):
    __tablename__ = "alerts"

    scope: Mapped[AlertScope] = mapped_column(Enum(AlertScope, name="alert_scope"),
                                              nullable=False)
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    pharmacy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pharmacies.id"))
    medication_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("medications.id"))
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), nullable=False)
    title_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    body_fr: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_alerts_scope_created", "scope", "created_at"),
        Index("ix_alerts_gov", "governorate_id"),
    )


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alerts.id"))
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        default=NotificationChannel.in_app,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_notifications_user", "user_id", "read_at"),)


class AuditLog(Base, UUIDMixin):
    """Append-only audit trail. No update/delete paths in the application."""

    __tablename__ = "audit_logs"

    user_sub: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str | None] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # HTTP method
    resource: Mapped[str] = mapped_column(String(255), nullable=False)  # path
    resource_id: Mapped[str | None] = mapped_column(String(64))
    status_code: Mapped[int | None] = mapped_column()
    ip: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_audit_logs_at", "at"),)
