"""Alert feed and acknowledgement."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role, Severity
from app.core.security import Principal, get_current_principal, require_roles
from app.models.ops import Alert
from app.models.reference import User
from app.schemas.entities import AlertOut
from app.services.labels import attach_labels

router = APIRouter()


@router.get("/alerts", response_model=list[AlertOut], summary="Role-scoped alert feed")
def list_alerts(
    severity: Severity | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[AlertOut]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)

    # Scope alerts: regional authorities see their governorate; pharmacists see
    # national + their own; PCT admins see everything.
    user = db.scalar(select(User).where(User.keycloak_sub == principal.sub))
    if user and principal.has_any(Role.regional_authority) and user.governorate_id:
        stmt = stmt.where(
            (Alert.governorate_id == user.governorate_id) | (Alert.governorate_id.is_(None))
        )
    if user and principal.has_any(Role.community_pharmacist, Role.hospital_pharmacist):
        if user.pharmacy_id:
            stmt = stmt.where(
                (Alert.pharmacy_id == user.pharmacy_id) | (Alert.scope == "national")
            )

    return attach_labels([AlertOut.model_validate(a) for a in db.scalars(stmt).all()], db)


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut, summary="Acknowledge an alert")
def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(
        require_roles(
            Role.pct_admin,
            Role.regional_authority,
            Role.hospital_pharmacist,
            Role.community_pharmacist,
        )
    ),
) -> AlertOut:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(404, "Alerte introuvable")
    user = db.scalar(select(User).where(User.keycloak_sub == principal.sub))
    alert.acknowledged_by = user.id if user else None
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return AlertOut.model_validate(alert)
