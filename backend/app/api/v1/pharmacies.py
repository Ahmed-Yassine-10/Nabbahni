"""Public pharmacy lookup incl. nearest-with-stock search.

Distance is computed with the haversine formula in Python so the endpoint is
portable across databases. On PostgreSQL this can be swapped for a PostGIS
`ST_DWithin` query against a geometry column for index-backed performance.
"""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import AvailabilityStatus
from app.models.reference import Pharmacy
from app.models.transactional import StockLevel
from app.schemas.entities import PharmacyNearby, PharmacyOut
from app.services.availability import availability_from_stock

router = APIRouter()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@router.get(
    "/pharmacies/nearby",
    response_model=list[PharmacyNearby],
    summary="Nearest pharmacies (optionally carrying a given medication)",
)
def nearby(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    medication: uuid.UUID | None = Query(None),
    radius_km: float = Query(25.0, ge=0.5, le=200),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PharmacyNearby]:
    pharmacies = db.scalars(select(Pharmacy)).all()

    scored = []
    for ph in pharmacies:
        if not ph.latitude and not ph.longitude:
            continue
        dist = _haversine_km(lat, lon, float(ph.latitude), float(ph.longitude))
        if dist <= radius_km:
            scored.append((dist, ph))
    scored.sort(key=lambda x: x[0])
    scored = scored[:limit]

    # Latest stock for the requested medication across the shortlisted pharmacies.
    stock_map: dict[uuid.UUID, StockLevel] = {}
    if medication is not None and scored:
        pharmacy_ids = [ph.id for _, ph in scored]
        latest = (
            select(
                StockLevel.pharmacy_id,
                func.max(StockLevel.recorded_at).label("d"),
            )
            .where(
                StockLevel.medication_id == medication,
                StockLevel.pharmacy_id.in_(pharmacy_ids),
            )
            .group_by(StockLevel.pharmacy_id)
            .subquery()
        )
        for sl in db.scalars(
            select(StockLevel).join(
                latest,
                (StockLevel.pharmacy_id == latest.c.pharmacy_id)
                & (StockLevel.recorded_at == latest.c.d),
            ).where(StockLevel.medication_id == medication)
        ).all():
            stock_map[sl.pharmacy_id] = sl

    result: list[PharmacyNearby] = []
    for dist, ph in scored:
        if medication is not None:
            sl = stock_map.get(ph.id)
            availability = (
                availability_from_stock(sl.quantity, sl.min_threshold)
                if sl
                else AvailabilityStatus.shortage
            )
            quantity = sl.quantity if sl else 0
        else:
            availability = AvailabilityStatus.available
            quantity = None
        result.append(
            PharmacyNearby(
                id=ph.id,
                name=ph.name,
                type=ph.type,
                address=ph.address,
                phone=ph.phone,
                distance_km=round(dist, 2),
                latitude=float(ph.latitude),
                longitude=float(ph.longitude),
                availability=availability,
                quantity=quantity,
            )
        )
    return result


@router.get("/pharmacies/{pharmacy_id}", response_model=PharmacyOut)
def get_pharmacy(pharmacy_id: uuid.UUID, db: Session = Depends(get_db)) -> PharmacyOut:
    pharm = db.get(Pharmacy, pharmacy_id)
    if pharm is None:
        raise HTTPException(404, "Pharmacie introuvable")
    return PharmacyOut.model_validate(pharm)
