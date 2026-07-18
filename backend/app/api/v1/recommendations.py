"""Recommendation listing and validation workflow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role, RecommendationStatus
from app.core.security import Principal, require_roles
from app.models.decision import Recommendation
from app.models.reference import User
from app.schemas.common import Page
from app.schemas.entities import RecommendationOut
from app.services.labels import attach_labels

router = APIRouter()

_DECISION_ROLES = (Role.pct_admin, Role.regional_authority)


def _resolve_user(db: Session, principal: Principal) -> User | None:
    return db.scalar(select(User).where(User.keycloak_sub == principal.sub))


@router.get("/recommendations", response_model=Page[RecommendationOut])
def list_recommendations(
    status: RecommendationStatus | None = Query(None),
    medication: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_DECISION_ROLES)),
) -> Page[RecommendationOut]:
    stmt = select(Recommendation)
    if status is not None:
        stmt = stmt.where(Recommendation.status == status)
    if medication is not None:
        stmt = stmt.where(Recommendation.medication_id == medication)

    count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Recommendation.confidence.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = attach_labels([RecommendationOut.model_validate(r) for r in rows], db)
    return Page(items=items, total=count, page=page, page_size=page_size)


def _transition(
    recommendation_id: uuid.UUID,
    new_status: RecommendationStatus,
    db: Session,
    principal: Principal,
) -> RecommendationOut:
    rec = db.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(404, "Recommandation introuvable")
    if rec.status != RecommendationStatus.proposed:
        raise HTTPException(409, f"Recommandation déjà {rec.status.value}")
    rec.status = new_status
    user = _resolve_user(db, principal)
    rec.validated_by = user.id if user else None
    rec.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return RecommendationOut.model_validate(rec)


@router.post("/recommendations/{recommendation_id}/validate", response_model=RecommendationOut)
def validate_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_DECISION_ROLES)),
) -> RecommendationOut:
    return _transition(recommendation_id, RecommendationStatus.validated, db, principal)


@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationOut)
def reject_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*_DECISION_ROLES)),
) -> RecommendationOut:
    return _transition(recommendation_id, RecommendationStatus.rejected, db, principal)
