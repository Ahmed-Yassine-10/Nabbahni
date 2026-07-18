"""Shortage predictions: list, detail, explanation, and national map (GeoJSON)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.database import get_db
from app.core.enums import Role, Severity
from app.core.security import Principal, require_roles
from app.models.ml import PredictionExplanation, ShortagePrediction
from app.models.reference import Governorate, Medication
from app.schemas.common import Page
from app.services.labels import attach_labels
from app.schemas.entities import (
    ExplanationOut,
    MedicationOut,
    ShortageDetail,
    ShortageOut,
)

router = APIRouter()

_VIEW_ROLES = (
    Role.pct_admin,
    Role.regional_authority,
    Role.hospital_pharmacist,
    Role.community_pharmacist,
)

_SEVERITY_COLOR = {
    "green": "#16a34a",
    "yellow": "#eab308",
    "orange": "#f97316",
    "red": "#dc2626",
    "critical": "#7f1d1d",
}


def _governorate_severity(ratio: float, crit_ratio: float) -> str:
    """Map the share of at-risk medications to a governorate risk level."""
    if crit_ratio >= 0.10 or ratio >= 0.22:
        return "critical"
    if ratio >= 0.12:
        return "red"
    if ratio >= 0.06:
        return "orange"
    if ratio >= 0.02:
        return "yellow"
    return "green"


@router.get("/shortages", response_model=Page[ShortageOut], summary="List shortage predictions")
def list_shortages(
    severity: Severity | None = Query(None),
    governorate: uuid.UUID | None = Query(None),
    atc: str | None = Query(None, description="ATC prefix filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_VIEW_ROLES)),
) -> Page[ShortageOut]:
    stmt = select(ShortagePrediction)
    if severity is not None:
        stmt = stmt.where(ShortagePrediction.severity == severity)
    if governorate is not None:
        stmt = stmt.where(ShortagePrediction.governorate_id == governorate)
    if atc:
        stmt = stmt.join(Medication, ShortagePrediction.medication_id == Medication.id).where(
            Medication.atc_code.like(f"{atc}%")
        )

    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ShortagePrediction.probability.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = attach_labels([ShortageOut.model_validate(r) for r in rows], db)
    return Page(items=items, total=count, page=page, page_size=page_size)


@router.get("/shortages/map", summary="National risk heatmap as GeoJSON")
def shortage_map(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.pct_admin, Role.regional_authority)),
) -> dict:
    if (cached := cache_get("shortage_map")) is not None:
        return cached

    # Aggregate max severity + counts per governorate in Python (small result set,
    # avoids dialect-specific ordering of the severity enum).
    preds = db.execute(
        select(
            ShortagePrediction.governorate_id,
            ShortagePrediction.severity,
        ).where(ShortagePrediction.governorate_id.isnot(None))
    ).all()

    by_gov: dict[uuid.UUID, dict] = {}
    for gov_id, severity in preds:
        entry = by_gov.setdefault(gov_id, {"max": Severity.green, "counts": {}, "total": 0})
        sev = severity if isinstance(severity, Severity) else Severity(severity)
        if sev >= entry["max"]:
            entry["max"] = sev
        entry["counts"][sev.value] = entry["counts"].get(sev.value, 0) + 1
        entry["total"] += 1

    governorates = db.scalars(select(Governorate)).all()

    features = []
    for gov in governorates:
        agg = by_gov.get(gov.id, {"max": Severity.green, "counts": {}, "total": 0})
        max_sev = agg["max"].value if isinstance(agg["max"], Severity) else agg["max"]
        counts = agg["counts"]
        total = agg["total"] or 1
        at_risk = sum(v for k, v in counts.items() if k in ("orange", "red", "critical"))
        critical_n = counts.get("critical", 0) + counts.get("red", 0)
        # Governorate-level severity reflects the SHARE of medications at risk,
        # not the single worst one — so the national heatmap shows a true gradient
        # instead of saturating to red. The worst single medication is still
        # available as `max_severity` for drill-down.
        ratio = at_risk / total
        crit_ratio = critical_n / total
        gov_sev = _governorate_severity(ratio, crit_ratio)
        features.append(
            {
                "type": "Feature",
                "geometry": gov.geojson,
                "properties": {
                    "governorate_id": str(gov.id),
                    "code": gov.code,
                    "name_fr": gov.name_fr,
                    "name_ar": gov.name_ar,
                    "centroid": [float(gov.centroid_lon), float(gov.centroid_lat)],
                    "severity": gov_sev,
                    "max_severity": max_sev,
                    "color": _SEVERITY_COLOR.get(gov_sev, "#16a34a"),
                    "at_risk_count": at_risk,
                    "risk_ratio": round(ratio, 3),
                    "counts": counts,
                    "total": agg["total"],
                },
            }
        )

    result = {"type": "FeatureCollection", "features": features}
    cache_set("shortage_map", result)
    return result


@router.get("/shortages/{shortage_id}", response_model=ShortageDetail)
def shortage_detail(shortage_id: uuid.UUID, db: Session = Depends(get_db),
                    principal: Principal = Depends(require_roles(*_VIEW_ROLES))) -> ShortageDetail:
    pred = db.get(ShortagePrediction, shortage_id)
    if pred is None:
        raise HTTPException(404, "Prédiction introuvable")
    med = db.get(Medication, pred.medication_id)
    detail = ShortageDetail.model_validate(pred)
    detail.medication = MedicationOut.model_validate(med) if med else None
    if pred.explanation:
        detail.explanation = ExplanationOut(
            top_factors=pred.explanation.top_factors or [],
            narrative_fr=pred.explanation.narrative_fr,
            narrative_ar=pred.explanation.narrative_ar,
        )
    return detail


@router.get("/shortages/{shortage_id}/explanation", response_model=ExplanationOut)
def shortage_explanation(
    shortage_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_VIEW_ROLES)),
) -> ExplanationOut:
    expl = db.scalar(
        select(PredictionExplanation).where(
            PredictionExplanation.shortage_prediction_id == shortage_id
        )
    )
    if expl is None:
        raise HTTPException(404, "Explication indisponible")
    return ExplanationOut(
        top_factors=expl.top_factors or [],
        narrative_fr=expl.narrative_fr,
        narrative_ar=expl.narrative_ar,
    )
