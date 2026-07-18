"""Expiry risk, waste projection, per-pharmacy allocation and redistribution."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.database import get_db
from app.core.enums import Role
from app.core.security import Principal, get_current_principal, require_roles
from app.models.reference import Medication, Pharmacy
from app.models.transactional import StockBatch
from app.schemas.expiry import (
    AllocationOut,
    BatchRiskOut,
    ExpiryAnalysisOut,
    ExpiryBandOut,
    PharmacyExpiryOut,
    TransferOut,
)
from app.services import expiry as expiry_service
from app.services.demand import pharmacy_daily_rates
from app.services.expiry import EXPIRY_BANDS, assess_batches, compute_allocation

router = APIRouter()

_STAFF = (Role.pct_admin, Role.regional_authority)
_PHARMACIST = (Role.community_pharmacist, Role.hospital_pharmacist)


def _medication_index(db: Session) -> dict[uuid.UUID, Medication]:
    return {m.id: m for m in db.scalars(select(Medication)).all()}


def _batches_for(db: Session, pharmacy_id: uuid.UUID | None) -> dict[uuid.UUID, list[dict]]:
    """Medication -> its lots, for one pharmacy (or the central warehouse)."""
    stmt = select(StockBatch).where(StockBatch.quantity > 0)
    stmt = stmt.where(
        StockBatch.pharmacy_id == pharmacy_id
        if pharmacy_id is not None
        else StockBatch.pharmacy_id.is_(None)
    )
    out: dict[uuid.UUID, list[dict]] = {}
    for b in db.scalars(stmt).all():
        out.setdefault(b.medication_id, []).append(
            {
                "id": b.id,
                "medication_id": b.medication_id,
                "pharmacy_id": b.pharmacy_id,
                "lot_number": b.lot_number,
                "quantity": b.quantity,
                "expiry_date": b.expiry_date,
            }
        )
    return out


@router.get(
    "/expiry/analysis",
    response_model=ExpiryAnalysisOut,
    summary="National expiry exposure: waste projection by band and worst cases",
)
def expiry_analysis(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_STAFF)),
) -> ExpiryAnalysisOut:
    if (cached := cache_get("expiry_analysis")) is not None:
        return ExpiryAnalysisOut(**cached)

    meds = _medication_index(db)
    today = date.today()

    band_counts = {label: [0, 0.0] for label, *_ in EXPIRY_BANDS}   # units, value
    total_units = 0
    total_value = 0.0
    at_risk_units = 0
    at_risk_value = 0.0
    expired_units = 0
    expired_value = 0.0
    worst: list[BatchRiskOut] = []

    pharmacies = db.scalars(select(Pharmacy)).all()
    for ph in pharmacies:
        rates = pharmacy_daily_rates(db, ph.id)
        for med_id, batches in _batches_for(db, ph.id).items():
            med = meds.get(med_id)
            if med is None:
                continue
            price = float(med.unit_price_tnd)
            risks = assess_batches(batches, rates.get(med_id, 0.0), price, today)
            for r in risks:
                total_units += r.quantity
                total_value += r.quantity * price
                label, _sev = expiry_service.band_for(r.days_to_expiry)
                band_counts[label][0] += r.quantity
                band_counts[label][1] += r.quantity * price
                if r.days_to_expiry <= 0:
                    expired_units += r.quantity
                    expired_value += r.quantity * price
                if r.at_risk_quantity > 0:
                    at_risk_units += r.at_risk_quantity
                    at_risk_value += r.at_risk_value_tnd
                    worst.append(
                        BatchRiskOut(
                            batch_id=r.batch_id,
                            medication_id=r.medication_id,
                            brand_name=med.brand_name,
                            dci=med.dci,
                            pharmacy_id=r.pharmacy_id,
                            pharmacy_name=ph.name,
                            lot_number=r.lot_number,
                            quantity=r.quantity,
                            expiry_date=r.expiry_date,
                            days_to_expiry=r.days_to_expiry,
                            daily_rate=r.daily_rate,
                            projected_consumption=r.projected_consumption,
                            at_risk_quantity=r.at_risk_quantity,
                            at_risk_value_tnd=r.at_risk_value_tnd,
                            severity=r.severity,
                        )
                    )

    worst.sort(key=lambda r: -r.at_risk_value_tnd)
    bands = [
        ExpiryBandOut(
            label=label,
            min_days=lo,
            max_days=hi,
            severity=sev,
            units=band_counts[label][0],
            value_tnd=round(band_counts[label][1], 2),
        )
        for label, lo, hi, sev in EXPIRY_BANDS
    ]

    result = ExpiryAnalysisOut(
        total_units=total_units,
        total_value_tnd=round(total_value, 2),
        at_risk_units=at_risk_units,
        at_risk_value_tnd=round(at_risk_value, 2),
        expired_units=expired_units,
        expired_value_tnd=round(expired_value, 2),
        waste_rate_pct=round(100 * at_risk_units / total_units, 2) if total_units else 0.0,
        bands=bands,
        worst_batches=worst[:25],
    )
    cache_set("expiry_analysis", result.model_dump(mode="json"))
    return result


@router.get(
    "/expiry/pharmacy/{pharmacy_id}",
    response_model=PharmacyExpiryOut,
    summary="Lots at risk and recommended order quantities for one pharmacy",
)
def pharmacy_expiry(
    pharmacy_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PharmacyExpiryOut:
    pharmacy = db.get(Pharmacy, pharmacy_id)
    if pharmacy is None:
        raise HTTPException(404, "Pharmacie introuvable")

    meds = _medication_index(db)
    rates = pharmacy_daily_rates(db, pharmacy_id)
    today = date.today()

    batch_out: list[BatchRiskOut] = []
    allocations: list[AllocationOut] = []

    for med_id, batches in _batches_for(db, pharmacy_id).items():
        med = meds.get(med_id)
        if med is None:
            continue
        price = float(med.unit_price_tnd)
        rate = rates.get(med_id, 0.0)
        risks = assess_batches(batches, rate, price, today)

        for r in risks:
            if r.at_risk_quantity > 0:
                batch_out.append(
                    BatchRiskOut(
                        batch_id=r.batch_id,
                        medication_id=r.medication_id,
                        brand_name=med.brand_name,
                        dci=med.dci,
                        pharmacy_id=str(pharmacy_id),
                        pharmacy_name=pharmacy.name,
                        lot_number=r.lot_number,
                        quantity=r.quantity,
                        expiry_date=r.expiry_date,
                        days_to_expiry=r.days_to_expiry,
                        daily_rate=r.daily_rate,
                        projected_consumption=r.projected_consumption,
                        at_risk_quantity=r.at_risk_quantity,
                        at_risk_value_tnd=r.at_risk_value_tnd,
                        severity=r.severity,
                    )
                )

        alloc = compute_allocation(
            medication_id=str(med_id),
            pharmacy_id=str(pharmacy_id),
            daily_rate=rate,
            batch_risks=risks,
            unit_price_tnd=price,
        )
        allocations.append(
            AllocationOut(
                medication_id=str(med_id),
                brand_name=med.brand_name,
                dci=med.dci,
                is_essential=med.is_essential,
                daily_rate=alloc.daily_rate,
                current_stock=alloc.current_stock,
                usable_stock=alloc.usable_stock,
                target_stock=alloc.target_stock,
                recommended_quantity=alloc.recommended_quantity,
                surplus_quantity=alloc.surplus_quantity,
                cover_days_after=(
                    None if alloc.cover_days_after == float("inf") else alloc.cover_days_after
                ),
                at_risk_quantity=alloc.at_risk_quantity,
                at_risk_value_tnd=alloc.at_risk_value_tnd,
                order_value_tnd=alloc.order_value_tnd,
                reason=alloc.reason,
            )
        )

    batch_out.sort(key=lambda r: r.days_to_expiry)
    allocations.sort(key=lambda a: -a.recommended_quantity)

    return PharmacyExpiryOut(
        pharmacy_id=str(pharmacy_id),
        pharmacy_name=pharmacy.name,
        at_risk_units=sum(b.at_risk_quantity for b in batch_out),
        at_risk_value_tnd=round(sum(b.at_risk_value_tnd for b in batch_out), 2),
        order_value_tnd=round(sum(a.order_value_tnd for a in allocations), 2),
        batches=batch_out,
        allocations=allocations,
    )


@router.get(
    "/expiry/redistribution",
    response_model=list[TransferOut],
    summary="Proposed transfers of soon-to-expire stock between pharmacies",
)
def redistribution(
    limit: int = Query(40, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_STAFF)),
) -> list[TransferOut]:
    meds = _medication_index(db)
    pharmacies = {p.id: p for p in db.scalars(select(Pharmacy)).all()}
    today = date.today()

    # Build allocations per medication across every pharmacy, then match
    # surplus against need.
    per_med_allocs: dict[uuid.UUID, list] = {}
    per_med_batches: dict[uuid.UUID, dict[str, list]] = {}

    for ph_id in pharmacies:
        rates = pharmacy_daily_rates(db, ph_id)
        for med_id, batches in _batches_for(db, ph_id).items():
            med = meds.get(med_id)
            if med is None:
                continue
            price = float(med.unit_price_tnd)
            risks = assess_batches(batches, rates.get(med_id, 0.0), price, today)
            alloc = compute_allocation(
                medication_id=str(med_id),
                pharmacy_id=str(ph_id),
                daily_rate=rates.get(med_id, 0.0),
                batch_risks=risks,
                unit_price_tnd=price,
            )
            per_med_allocs.setdefault(med_id, []).append(alloc)
            per_med_batches.setdefault(med_id, {})[str(ph_id)] = risks

    out: list[TransferOut] = []
    for med_id, allocs in per_med_allocs.items():
        med = meds[med_id]
        donors = [a for a in allocs if a.at_risk_quantity > 0]
        receivers = [a for a in allocs if a.recommended_quantity > 0]
        if not donors or not receivers:
            continue
        for t in expiry_service.propose_transfers(
            str(med_id), donors, receivers, per_med_batches[med_id],
            float(med.unit_price_tnd),
        ):
            out.append(
                TransferOut(
                    medication_id=t.medication_id,
                    brand_name=med.brand_name,
                    from_pharmacy_id=t.from_pharmacy_id,
                    from_pharmacy_name=pharmacies[uuid.UUID(t.from_pharmacy_id)].name,
                    to_pharmacy_id=t.to_pharmacy_id,
                    to_pharmacy_name=pharmacies[uuid.UUID(t.to_pharmacy_id)].name,
                    quantity=t.quantity,
                    expiry_date=t.expiry_date,
                    days_to_expiry=t.days_to_expiry,
                    value_saved_tnd=t.value_saved_tnd,
                    rationale=t.rationale,
                )
            )

    out.sort(key=lambda t: (t.days_to_expiry, -t.value_saved_tnd))
    return out[:limit]
