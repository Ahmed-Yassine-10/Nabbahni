"""Authentication introspection + development login."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.enums import Role
from app.core.security import Principal, get_current_principal
from app.models.reference import User
from app.schemas.entities import MeOut

router = APIRouter()


@router.get("/me", response_model=MeOut, summary="Current authenticated user")
def me(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MeOut:
    user = db.scalar(select(User).where(User.keycloak_sub == principal.sub))
    return MeOut(
        sub=principal.sub,
        email=principal.email,
        roles=sorted(principal.roles),
        pharmacy_id=user.pharmacy_id if user else None,
        governorate_id=user.governorate_id if user else None,
        supplier_id=user.supplier_id if user else None,
    )


class DevLoginRequest(BaseModel):
    role: Role
    email: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post(
    "/auth/dev-login",
    response_model=TokenResponse,
    summary="Development login (issues a local JWT; disabled when Keycloak is on)",
)
def dev_login(payload: DevLoginRequest) -> TokenResponse:
    """Issue a short-lived HS256 token for a chosen role.

    Only available when KEYCLOAK_ENABLED=false. In production, authentication
    goes through Keycloak (OIDC) and this endpoint refuses to issue tokens.
    """
    if settings.keycloak_enabled:
        raise HTTPException(403, "Dev login désactivé : utilisez Keycloak.")

    email = payload.email or f"{payload.role.value}@demo.tn"
    # Match seeded demo users so pharmacy/governorate links resolve.
    demo_subjects = {
        Role.pct_admin: "admin@pct.tn",
        Role.regional_authority: "region.tunis@sante.tn",
        Role.hospital_pharmacist: "hopital.charlesnicolle@sante.tn",
        Role.community_pharmacist: "pharmacie.elmanar@pharma.tn",
        Role.supplier: "supplier.medis@medis.tn",
        Role.citizen: "citoyen@demo.tn",
    }
    sub = demo_subjects.get(payload.role, email)
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": sub,
            "email": sub,
            "roles": [payload.role.value],
            "realm_access": {"roles": [payload.role.value]},
            "iat": now,
            "exp": now + 12 * 3600,
        },
        settings.secret_key,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, role=payload.role.value)
