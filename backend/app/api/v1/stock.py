"""Pharmacy + national stock endpoints and ingestion."""
from __future__ import annotations

import statistics
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.database import get_db
from app.core.enums import Role
from app.core.messaging import publish_ingest
from app.core.security import Principal, get_current_principal, require_roles
from app.models.ml import ShortagePrediction
from app.models.reference import Medication
from app.models.transactional import NationalStock, StockLevel
from app.schemas.entities import (
    NationalStockOut,
    StockAnalysisBucket,
    StockAnalysisOut,
    StockIngestRequest,
    StockOut,
)
from app.services.demand import pharmacy_daily_rates
from app.services.labels import attach_labels

router = APIRouter()

_STAFF = (Role.pct_admin, Role.regional_authority)


@router.get("/stock/pharmacy/{pharmacy_id}", response_model=list[StockOut])
def pharmacy_stock(
    pharmacy_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[StockOut]:
    # Latest stock row per medication for this pharmacy.
    latest = (
        select(
            StockLevel.medication_id,
            func.max(StockLevel.recorded_at).label("max_date"),
        )
        .where(StockLevel.pharmacy_id == pharmacy_id)
        .group_by(StockLevel.medication_id)
        .subquery()
    )
    rows = db.scalars(
        select(StockLevel)
        .join(
            latest,
            (StockLevel.medication_id == latest.c.medication_id)
            & (StockLevel.recorded_at == latest.c.max_date),
        )
        .where(StockLevel.pharmacy_id == pharmacy_id)
    ).all()

    items = attach_labels([StockOut.model_validate(r) for r in rows], db)
    _attach_coverage(db, pharmacy_id, items)
    return items


def _attach_coverage(db: Session, pharmacy_id: uuid.UUID, items: list[StockOut]) -> None:
    """Set `coverage_days` = stock / this pharmacy's estimated daily consumption."""
    rates = pharmacy_daily_rates(db, pharmacy_id)
    for item in items:
        rate = rates.get(item.medication_id, 0.0)
        item.coverage_days = round(item.quantity / rate, 1) if rate > 0 else None


@router.post("/stock/pharmacy/{pharmacy_id}", status_code=202, summary="Ingest stock levels")
def ingest_stock(
    pharmacy_id: uuid.UUID,
    payload: StockIngestRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(
        require_roles(Role.community_pharmacist, Role.hospital_pharmacist, Role.pct_admin)
    ),
) -> dict[str, int]:
    today = date.today()
    for item in payload.items:
        recorded_at = item.recorded_at or today
        existing = db.scalar(
            select(StockLevel).where(
                StockLevel.pharmacy_id == pharmacy_id,
                StockLevel.medication_id == item.medication_id,
                StockLevel.recorded_at == recorded_at,
            )
        )
        if existing:
            existing.quantity = item.quantity
            existing.min_threshold = item.min_threshold
        else:
            db.add(StockLevel(
                pharmacy_id=pharmacy_id,
                medication_id=item.medication_id,
                quantity=item.quantity,
                min_threshold=item.min_threshold,
                recorded_at=recorded_at,
            ))
    db.commit()
    publish_ingest({"type": "stock", "pharmacy_id": str(pharmacy_id), "count": len(payload.items)})
    return {"ingested": len(payload.items)}


@router.get(
    "/stock/national",
    response_model=list[NationalStockOut],
    summary="National inventory with coverage estimate",
)
def national_stock(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_STAFF)),
) -> list[NationalStockOut]:
    cache_key = f"national_stock:{limit}"
    if (cached := cache_get(cache_key)) is not None:
        return [NationalStockOut(**row) for row in cached]

    latest = (
        select(
            NationalStock.medication_id,
            func.max(NationalStock.recorded_at).label("max_date"),
        )
        .group_by(NationalStock.medication_id)
        .subquery()
    )
    rows = db.execute(
        select(NationalStock, Medication)
        .join(Medication, NationalStock.medication_id == Medication.id)
        .join(
            latest,
            (NationalStock.medication_id == latest.c.medication_id)
            & (NationalStock.recorded_at == latest.c.max_date),
        )
        .limit(limit)
    ).all()

    # Attach coverage_days from the latest shortage prediction where available.
    coverage = {
        r.medication_id: float(r.coverage_days)
        for r in db.execute(
            select(
                ShortagePrediction.medication_id,
                ShortagePrediction.coverage_days,
            ).where(ShortagePrediction.governorate_id.is_(None))
        ).all()
        if r.coverage_days is not None
    }

    result = [
        NationalStockOut(
            medication_id=ns.medication_id,
            brand_name=med.brand_name,
            dci=med.dci,
            quantity=ns.quantity,
            coverage_days=coverage.get(ns.medication_id),
            recorded_at=ns.recorded_at,
            is_essential=med.is_essential,
            unit_price_tnd=float(med.unit_price_tnd),
        )
        for ns, med in rows
    ]
    cache_set(cache_key, [r.model_dump() for r in result])
    return result


# Coverage bands used by the stock-analysis view. Thresholds mirror the
# shortage engine: under 5 days is the same line that forces `critical`
# severity for essential medications.
_COVERAGE_BANDS: list[tuple[str, float, float | None, str]] = [
    ("Rupture imminente", 0.0, 5.0, "critical"),
    ("Critique", 5.0, 15.0, "red"),
    ("Tendu", 15.0, 30.0, "orange"),
    ("Surveillance", 30.0, 60.0, "yellow"),
    ("Confortable", 60.0, None, "green"),
]


@router.get(
    "/stock/analysis",
    response_model=StockAnalysisOut,
    summary="National inventory analysis: value, coverage distribution, worst cases",
)
def stock_analysis(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_STAFF)),
) -> StockAnalysisOut:
    if (cached := cache_get("stock_analysis")) is not None:
        return StockAnalysisOut(**cached)

    rows = national_stock(limit=1000, db=db, principal=principal)

    total_units = sum(r.quantity for r in rows)
    total_value = sum(r.quantity * r.unit_price_tnd for r in rows)
    covers = [r.coverage_days for r in rows if r.coverage_days is not None]
    median_cover = statistics.median(covers) if covers else 0.0

    buckets = []
    for label, lo, hi, severity in _COVERAGE_BANDS:
        count = sum(
            1
            for c in covers
            if c >= lo and (hi is None or c < hi)
        )
        buckets.append(
            StockAnalysisBucket(
                label=label, min_days=lo, max_days=hi, count=count, severity=severity
            )
        )

    essential_at_risk = sum(
        1
        for r in rows
        if r.is_essential and r.coverage_days is not None and r.coverage_days < 15
    )

    worst = sorted(
        (r for r in rows if r.coverage_days is not None),
        key=lambda r: r.coverage_days,
    )[:15]

    result = StockAnalysisOut(
        total_medications=len(rows),
        total_units=total_units,
        total_value_tnd=round(total_value, 2),
        median_coverage_days=round(median_cover, 1),
        essential_at_risk=essential_at_risk,
        buckets=buckets,
        lowest_coverage=worst,
    )
    cache_set("stock_analysis", result.model_dump(mode="json"))
    return result
