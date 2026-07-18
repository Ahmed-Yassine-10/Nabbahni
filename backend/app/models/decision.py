"""Decision-support models: recommendations and substitutions."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from app.core.enums import EquivalenceLevel, RecommendationStatus, RecommendationType


class Recommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommendations"

    shortage_prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shortage_predictions.id")
    )
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    rec_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type"), nullable=False
    )
    title_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    detail_fr: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    financial_impact_tnd: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    expected_shortage_reduction_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    suggested_quantity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"),
        default=RecommendationStatus.proposed,
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_recommendations_status", "status"),
        Index("ix_recommendations_med", "medication_id"),
    )


class Substitution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "substitutions"

    source_medication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medications.id"), nullable=False
    )
    target_medication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medications.id"), nullable=False
    )
    atc_match_level: Mapped[int] = mapped_column(Integer, default=5)  # 3,4,5 = deeper match
    equivalence: Mapped[EquivalenceLevel] = mapped_column(
        Enum(EquivalenceLevel, name="equivalence_level"), nullable=False
    )
    ddd_ratio: Mapped[float | None] = mapped_column(Numeric(8, 3))
    notes_fr: Mapped[str | None] = mapped_column(Text)
    requires_pharmacist_validation: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source_medication_id", "target_medication_id",
                         name="uq_substitution_pair"),
        Index("ix_substitutions_source", "source_medication_id"),
    )
