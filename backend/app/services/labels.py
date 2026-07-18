"""Lookup helpers that attach human-readable labels to list payloads.

Rows keyed only by UUID are unreadable in a UI. Rather than issuing one query
per row (N+1) or joining in every endpoint by hand, each list endpoint loads
the two small reference tables once and stamps the labels on its response.
Both tables are tiny (hundreds of medications, 24 governorates), so a single
full fetch is cheaper than a join per request.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Governorate, Medication
from app.schemas.entities import MedicationBrief


def medication_briefs(
    db: Session, ids: Iterable[uuid.UUID] | None = None
) -> dict[uuid.UUID, MedicationBrief]:
    """Map medication id -> brief. Pass `ids` to restrict the fetch."""
    stmt = select(Medication)
    if ids is not None:
        id_list = [i for i in ids if i is not None]
        if not id_list:
            return {}
        stmt = stmt.where(Medication.id.in_(id_list))
    return {m.id: MedicationBrief.model_validate(m) for m in db.scalars(stmt).all()}


def governorate_name_map(db: Session) -> dict[uuid.UUID, str]:
    """Map governorate id -> French name."""
    rows = db.execute(select(Governorate.id, Governorate.name_fr)).all()
    return {gid: name for gid, name in rows}


def attach_labels(items: list, db: Session) -> list:
    """Stamp `medication` and `governorate_name` onto any rows that expose
    `medication_id` / `governorate_id` fields."""
    meds = medication_briefs(db, [getattr(i, "medication_id", None) for i in items])
    govs = governorate_name_map(db)
    for item in items:
        med_id = getattr(item, "medication_id", None)
        if med_id is not None and hasattr(item, "medication"):
            item.medication = meds.get(med_id)
        gov_id = getattr(item, "governorate_id", None)
        if gov_id is not None and hasattr(item, "governorate_name"):
            item.governorate_name = govs.get(gov_id)
    return items
