"""ML output models: model runs, forecasts, shortage predictions, explanations."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.dbtypes import JSONType
from app.core.enums import Severity, Trend


class ModelRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "model_runs"

    mlflow_run_id: Mapped[str | None] = mapped_column(String(64))
    model_family: Mapped[str] = mapped_column(String(40), nullable=False)  # xgboost/lightgbm/prophet
    model_type: Mapped[str] = mapped_column(String(40), default="demand")  # demand/shortage
    horizon_days: Mapped[int | None] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Forecast(Base, UUIDMixin):
    __tablename__ = "forecasts"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    # NULL governorate_id => national aggregate.
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_qty: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    ci_lower: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    ci_upper: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    trend: Mapped[Trend] = mapped_column(Enum(Trend, name="trend"), default=Trend.stable)
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_runs.id"))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_forecasts_med_gov_h", "medication_id", "governorate_id", "horizon_days"),
    )


class ShortagePrediction(Base, UUIDMixin):
    __tablename__ = "shortage_predictions"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id"), nullable=False)
    governorate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("governorates.id"))
    horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    probability: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), nullable=False)
    estimated_shortage_date: Mapped[date | None] = mapped_column(Date)
    coverage_days: Mapped[float | None] = mapped_column(Numeric(8, 2))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_runs.id"))

    explanation: Mapped["PredictionExplanation"] = relationship(
        back_populates="prediction", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_shortage_pred_sev_time", "severity", "computed_at"),
        Index("ix_shortage_pred_gov", "governorate_id"),
        Index("ix_shortage_pred_med", "medication_id"),
    )


class PredictionExplanation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "prediction_explanations"

    shortage_prediction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shortage_predictions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    shap_values: Mapped[dict] = mapped_column(JSONType, default=dict)
    top_factors: Mapped[list] = mapped_column(JSONType, default=list)
    narrative_fr: Mapped[str | None] = mapped_column(Text)
    narrative_ar: Mapped[str | None] = mapped_column(Text)

    prediction: Mapped[ShortagePrediction] = relationship(back_populates="explanation")
