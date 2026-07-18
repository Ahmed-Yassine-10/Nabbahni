"""Audit middleware — records mutating requests to the append-only audit log."""
from __future__ import annotations

import contextlib

from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import SessionLocal
from app.models.ops import AuditLog

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _peek_identity(request: Request) -> tuple[str | None, str | None]:
    """Best-effort extraction of sub/role from the bearer token without verifying.

    Verification already happened (or will) in the route dependency; the audit
    log only needs to attribute the action, so an unverified peek is acceptable
    and avoids coupling the middleware to Keycloak availability.
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None, None
    token = auth.split(" ", 1)[1]
    with contextlib.suppress(Exception):
        claims = jwt.get_unverified_claims(token)
        realm_access = claims.get("realm_access") or {}
        roles = realm_access.get("roles") or claims.get("roles") or []
        role = roles[0] if roles else None
        return claims.get("sub"), role
    return None, None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method in _MUTATING_METHODS and not request.url.path.endswith("/metrics"):
            sub, role = _peek_identity(request)
            client_ip = request.client.host if request.client else None
            try:
                db = SessionLocal()
                db.add(
                    AuditLog(
                        user_sub=sub,
                        role=role,
                        action=request.method,
                        resource=request.url.path,
                        resource_id=request.path_params.get("id")
                        if hasattr(request, "path_params")
                        else None,
                        status_code=response.status_code,
                        ip=client_ip,
                    )
                )
                db.commit()
            except Exception:  # audit must never break the request path
                with contextlib.suppress(Exception):
                    db.rollback()
            finally:
                with contextlib.suppress(Exception):
                    db.close()

        return response
