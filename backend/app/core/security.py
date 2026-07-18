"""Authentication & authorization: Keycloak JWT validation + RBAC dependencies.

Two modes:
  * KEYCLOAK_ENABLED=true  -> validate RS256 tokens against the realm JWKS.
  * KEYCLOAK_ENABLED=false -> accept a signed local dev token (HS256) so the API
    is testable without a running Keycloak. Never enable dev mode in production.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.enums import Role

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """The authenticated caller extracted from a validated token."""

    sub: str
    email: str | None
    roles: set[str] = field(default_factory=set)
    org: str | None = None

    def has_any(self, *roles: Role | str) -> bool:
        wanted = {r.value if isinstance(r, Role) else r for r in roles}
        return bool(self.roles & wanted)


class _JwksCache:
    """Small in-process cache of the realm's JSON Web Key Set."""

    def __init__(self, ttl: int = 3600) -> None:
        self._keys: dict | None = None
        self._fetched_at: float = 0.0
        self._ttl = ttl

    def get(self) -> dict:
        now = time.time()
        if self._keys is None or now - self._fetched_at > self._ttl:
            resp = httpx.get(settings.keycloak_jwks_url, timeout=5.0)
            resp.raise_for_status()
            self._keys = resp.json()
            self._fetched_at = now
        return self._keys


_jwks_cache = _JwksCache()


def _decode_keycloak(token: str) -> dict:
    jwks = _jwks_cache.get()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:  # pragma: no cover - malformed token
        raise _unauthorized("Token malformé") from exc

    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key is None:
        _jwks_cache._keys = None  # force refresh on next call (key rotation)
        raise _unauthorized("Clé de signature inconnue")

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.keycloak_api_client_id,
            issuer=settings.keycloak_realm_url,
            options={"verify_aud": False},  # audience mapper varies; role check is the gate
        )
    except JWTError as exc:
        raise _unauthorized(f"Token invalide: {exc}") from exc


def _decode_dev(token: str) -> dict:
    """Local development token signed with the app secret (HS256)."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise _unauthorized(f"Token dev invalide: {exc}") from exc


def _extract_roles(claims: dict) -> set[str]:
    realm_access = claims.get("realm_access") or {}
    roles = set(realm_access.get("roles", []))
    # dev tokens may carry a flat "roles" list
    roles |= set(claims.get("roles", []))
    return roles


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None:
        raise _unauthorized("Authentification requise")

    token = credentials.credentials
    claims = _decode_keycloak(token) if settings.keycloak_enabled else _decode_dev(token)

    return Principal(
        sub=claims.get("sub", "unknown"),
        email=claims.get("email"),
        roles=_extract_roles(claims),
        org=claims.get("org"),
    )


def get_optional_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal | None:
    """For public endpoints that personalize output when a token is present."""
    if credentials is None:
        return None
    try:
        return get_current_principal(credentials)
    except HTTPException:
        return None


def require_roles(*roles: Role):
    """Dependency factory enforcing that the caller holds at least one role."""

    def _dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : rôle insuffisant.",
            )
        return principal

    return _dependency
