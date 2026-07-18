"""Demand forecast retrieval."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.security import Principal, require_roles
from app.models.ml import Forecast
from app.schemas.entities import ForecastOut

router = APIRouter()


@router.get("/forecasts", response_model=list[ForecastOut], summary="Demand forecasts")
def list_forecasts(
    medication: uuid.UUID,
    governorate: uuid.UUID | None = Query(None, description="Omit for national forecast"),
    horizon: int | None = Query(None, description="1/2 week, 1/3 month => 7/14/30/90 days"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(
        require_roles(
            Role.pct_admin,
            Role.regional_authority,
            Role.hospital_pharmacist,
            Role.community_pharmacist,
        )
    ),
) -> list[ForecastOut]:
    stmt = select(Forecast).where(Forecast.medication_id == medication)
    stmt = (
        stmt.where(Forecast.governorate_id == governorate)
        if governorate is not None
        else stmt.where(Forecast.governorate_id.is_(None))
    )
    if horizon is not None:
        stmt = stmt.where(Forecast.horizon_days == horizon)
    stmt = stmt.order_by(Forecast.horizon_days, Forecast.forecast_date)
    return [ForecastOut.model_validate(r) for r in db.scalars(stmt).all()]
