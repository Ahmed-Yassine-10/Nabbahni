"""Sales ingestion and time-series retrieval."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.messaging import publish_ingest
from app.core.security import Principal, require_roles
from app.models.reference import Pharmacy
from app.models.transactional import SalesDaily
from app.schemas.entities import SalesIngestRequest, SalesPoint

router = APIRouter()


@router.post("/sales/ingest", status_code=202, summary="Ingest daily sales")
def ingest_sales(
    payload: SalesIngestRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(
        require_roles(Role.community_pharmacist, Role.hospital_pharmacist, Role.pct_admin)
    ),
) -> dict[str, int]:
    for item in payload.items:
        existing = db.scalar(
            select(SalesDaily).where(
                SalesDaily.pharmacy_id == item.pharmacy_id,
                SalesDaily.medication_id == item.medication_id,
                SalesDaily.date == item.date,
            )
        )
        if existing:
            existing.quantity = item.quantity
            existing.revenue_tnd = item.revenue_tnd
        else:
            db.add(SalesDaily(
                pharmacy_id=item.pharmacy_id,
                medication_id=item.medication_id,
                date=item.date,
                quantity=item.quantity,
                revenue_tnd=item.revenue_tnd,
            ))
    db.commit()
    publish_ingest({"type": "sales", "count": len(payload.items)})
    return {"ingested": len(payload.items)}


@router.get(
    "/sales/series",
    response_model=list[SalesPoint],
    summary="National (or governorate) daily sales series for a medication",
)
def sales_series(
    medication: uuid.UUID,
    governorate: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.pct_admin, Role.regional_authority)),
) -> list[SalesPoint]:
    stmt = (
        select(
            SalesDaily.date,
            func.sum(SalesDaily.quantity).label("qty"),
            func.sum(SalesDaily.revenue_tnd).label("rev"),
        )
        .where(SalesDaily.medication_id == medication)
        .group_by(SalesDaily.date)
        .order_by(SalesDaily.date)
    )
    if governorate is not None:
        stmt = stmt.join(Pharmacy, SalesDaily.pharmacy_id == Pharmacy.id).where(
            Pharmacy.governorate_id == governorate
        )

    rows = db.execute(stmt).all()
    return [SalesPoint(date=r.date, quantity=int(r.qty), revenue_tnd=float(r.rev)) for r in rows]
