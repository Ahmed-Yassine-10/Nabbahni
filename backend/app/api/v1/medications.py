"""Medication catalogue endpoints (public search) + substitutions lookup."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.models.decision import Substitution
from app.models.reference import Medication
from app.schemas.common import Page
from app.schemas.entities import MedicationOut, SubstitutionOut

router = APIRouter()


@router.get("/medications", response_model=Page[MedicationOut], summary="Search medications")
def list_medications(
    q: str | None = Query(None, description="Free-text search on brand name / DCI"),
    atc: str | None = Query(None, description="ATC code prefix filter"),
    essential: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> Page[MedicationOut]:
    stmt = select(Medication)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Medication.brand_name.ilike(like), Medication.dci.ilike(like)))
    if atc:
        stmt = stmt.where(Medication.atc_code.like(f"{atc}%"))
    if essential is not None:
        stmt = stmt.where(Medication.is_essential.is_(essential))

    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Medication.brand_name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page(items=[MedicationOut.model_validate(r) for r in rows], total=count,
                page=page, page_size=page_size)


@router.get("/medications/{medication_id}", response_model=MedicationOut)
def get_medication(medication_id: uuid.UUID, db: Session = Depends(get_db)) -> MedicationOut:
    med = db.get(Medication, medication_id)
    if med is None:
        raise HTTPException(404, "Médicament introuvable")
    return MedicationOut.model_validate(med)


@router.get(
    "/medications/{medication_id}/substitutions",
    response_model=list[SubstitutionOut],
    summary="Therapeutic substitution candidates (pharmacist validates)",
)
def get_substitutions(
    medication_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[SubstitutionOut]:
    if db.get(Medication, medication_id) is None:
        raise HTTPException(404, "Médicament introuvable")

    target = aliased(Medication)
    rows = db.execute(
        select(Substitution, target)
        .join(target, Substitution.target_medication_id == target.id)
        .where(Substitution.source_medication_id == medication_id)
        .order_by(Substitution.atc_match_level.desc())
    ).all()

    return [
        SubstitutionOut(
            id=sub.id,
            target=MedicationOut.model_validate(med),
            atc_match_level=sub.atc_match_level,
            equivalence=sub.equivalence,
            ddd_ratio=float(sub.ddd_ratio) if sub.ddd_ratio is not None else None,
            notes_fr=sub.notes_fr,
            requires_pharmacist_validation=sub.requires_pharmacist_validation,
        )
        for sub, med in rows
    ]
