"""Public citizen-facing availability search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.core.cache import cache_get, cache_set
from app.core.database import get_db
from app.core.enums import AvailabilityStatus, Severity
from app.models.decision import Substitution
from app.models.ml import ShortagePrediction
from app.models.reference import Governorate, Medication
from app.schemas.entities import (
    CitizenAvailabilityOut,
    CitizenAvailabilityRow,
    MedicationOut,
    SubstitutionOut,
)
from app.services.availability import availability_from_severity

router = APIRouter()


@router.get(
    "/citizen/availability",
    response_model=CitizenAvailabilityOut,
    summary="Public medication availability by governorate + alternatives",
)
def availability(
    q: str = Query(..., min_length=2, description="Nom commercial ou DCI du médicament"),
    db: Session = Depends(get_db),
) -> CitizenAvailabilityOut:
    cache_key = f"citizen_avail:{q.lower()}"
    if (cached := cache_get(cache_key)) is not None:
        return CitizenAvailabilityOut(**cached)

    like = f"%{q}%"
    med = db.scalar(
        select(Medication)
        .where(or_(Medication.brand_name.ilike(like), Medication.dci.ilike(like)))
        .order_by(Medication.brand_name)
        .limit(1)
    )
    if med is None:
        raise HTTPException(404, "Aucun médicament ne correspond à cette recherche")

    # Per-governorate severity from current predictions.
    gov_severity = {
        row.governorate_id: row.severity
        for row in db.execute(
            select(ShortagePrediction.governorate_id, ShortagePrediction.severity).where(
                ShortagePrediction.medication_id == med.id,
                ShortagePrediction.governorate_id.isnot(None),
            )
        ).all()
    }

    governorates = db.scalars(select(Governorate).order_by(Governorate.name_fr)).all()
    rows: list[CitizenAvailabilityRow] = []
    worst = Severity.green
    for gov in governorates:
        sev = gov_severity.get(gov.id, Severity.green)
        sev = sev if isinstance(sev, Severity) else Severity(sev)
        if sev >= worst:
            worst = sev
        rows.append(
            CitizenAvailabilityRow(
                governorate=gov.name_fr,
                availability=availability_from_severity(sev),
                pharmacies_with_stock=0,   # populated by pharmacy stock join in later pass
                total_pharmacies=0,
            )
        )

    national_status = availability_from_severity(worst)

    # Suggest alternatives when the medication is under pressure.
    alternatives: list[SubstitutionOut] = []
    if national_status != AvailabilityStatus.available:
        target = aliased(Medication)
        sub_rows = db.execute(
            select(Substitution, target)
            .join(target, Substitution.target_medication_id == target.id)
            .where(Substitution.source_medication_id == med.id)
            .order_by(Substitution.atc_match_level.desc())
            .limit(4)
        ).all()
        alternatives = [
            SubstitutionOut(
                id=sub.id,
                target=MedicationOut.model_validate(t),
                atc_match_level=sub.atc_match_level,
                equivalence=sub.equivalence,
                ddd_ratio=float(sub.ddd_ratio) if sub.ddd_ratio is not None else None,
                notes_fr=sub.notes_fr,
                requires_pharmacist_validation=sub.requires_pharmacist_validation,
            )
            for sub, t in sub_rows
        ]

    result = CitizenAvailabilityOut(
        medication=MedicationOut.model_validate(med),
        national_status=national_status,
        by_governorate=rows,
        alternatives=alternatives,
    )
    cache_set(cache_key, result.model_dump())
    return result
