"""Per-pharmacy consumption rates.

Sales reach the platform aggregated by governorate — the ETL receives regional
totals from the distribution chain, not per-counter scans. So a single
pharmacy's consumption is never observed directly and has to be inferred.

We apportion regional demand by the pharmacy's share of regional stock: a
pharmacy holding 10% of a governorate's stock of a medication is assumed to
serve roughly 10% of that governorate's demand for it. Crude, but stable, and
far closer than the alternative — dividing one pharmacy's stock by the whole
region's demand, which made every shelf in the country read "2 days of cover".

Replace this module wholesale once per-pharmacy sales are ingested for real;
nothing else needs to change.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reference import Pharmacy
from app.models.transactional import SalesDaily, StockLevel

# Trailing window used to estimate consumption.
CONSUMPTION_WINDOW_DAYS = 30


def _latest_stock_subquery(pharmacy_ids: list[uuid.UUID]):
    return (
        select(
            StockLevel.pharmacy_id.label("ph"),
            StockLevel.medication_id.label("med"),
            func.max(StockLevel.recorded_at).label("max_date"),
        )
        .where(StockLevel.pharmacy_id.in_(pharmacy_ids))
        .group_by(StockLevel.pharmacy_id, StockLevel.medication_id)
        .subquery()
    )


def regional_daily_demand(
    db: Session, governorate_id: uuid.UUID, window_days: int = CONSUMPTION_WINDOW_DAYS
) -> dict[uuid.UUID, float]:
    """Medication -> mean daily units sold across a governorate."""
    peer_ids = [
        p for (p,) in db.execute(
            select(Pharmacy.id).where(Pharmacy.governorate_id == governorate_id)
        ).all()
    ]
    if not peer_ids:
        return {}
    since = date.today() - timedelta(days=window_days)
    return {
        med_id: (qty or 0) / float(window_days)
        for med_id, qty in db.execute(
            select(SalesDaily.medication_id, func.sum(SalesDaily.quantity))
            .where(SalesDaily.pharmacy_id.in_(peer_ids), SalesDaily.date >= since)
            .group_by(SalesDaily.medication_id)
        ).all()
    }


def regional_stock(db: Session, governorate_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Medication -> total units held across a governorate (latest snapshot)."""
    peer_ids = [
        p for (p,) in db.execute(
            select(Pharmacy.id).where(Pharmacy.governorate_id == governorate_id)
        ).all()
    ]
    if not peer_ids:
        return {}
    latest = _latest_stock_subquery(peer_ids)
    return {
        med_id: total or 0
        for med_id, total in db.execute(
            select(StockLevel.medication_id, func.sum(StockLevel.quantity))
            .join(
                latest,
                (StockLevel.pharmacy_id == latest.c.ph)
                & (StockLevel.medication_id == latest.c.med)
                & (StockLevel.recorded_at == latest.c.max_date),
            )
            .group_by(StockLevel.medication_id)
        ).all()
    }


def pharmacy_stock(db: Session, pharmacy_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Medication -> units held by one pharmacy (latest snapshot)."""
    latest = _latest_stock_subquery([pharmacy_id])
    return {
        med_id: qty or 0
        for med_id, qty in db.execute(
            select(StockLevel.medication_id, StockLevel.quantity)
            .join(
                latest,
                (StockLevel.pharmacy_id == latest.c.ph)
                & (StockLevel.medication_id == latest.c.med)
                & (StockLevel.recorded_at == latest.c.max_date),
            )
            .where(StockLevel.pharmacy_id == pharmacy_id)
        ).all()
    }


def pharmacy_daily_rates(
    db: Session, pharmacy_id: uuid.UUID, window_days: int = CONSUMPTION_WINDOW_DAYS
) -> dict[uuid.UUID, float]:
    """Medication -> estimated daily units consumed by one pharmacy."""
    pharmacy = db.get(Pharmacy, pharmacy_id)
    if pharmacy is None:
        return {}

    gov_daily = regional_daily_demand(db, pharmacy.governorate_id, window_days)
    gov_stock = regional_stock(db, pharmacy.governorate_id)
    own_stock = pharmacy_stock(db, pharmacy_id)

    rates: dict[uuid.UUID, float] = {}
    for med_id, own in own_stock.items():
        regional_rate = gov_daily.get(med_id, 0.0)
        regional_total = gov_stock.get(med_id, 0)
        if regional_rate <= 0 or regional_total <= 0 or own <= 0:
            rates[med_id] = 0.0
            continue
        rates[med_id] = regional_rate * (own / regional_total)
    return rates
