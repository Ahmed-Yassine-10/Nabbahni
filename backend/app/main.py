"""SentinelleRx FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.audit import AuditMiddleware
from app.core.config import settings
from app.core.observability import setup_observability

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("sentinellerx")

limiter = Limiter(key_func=get_remote_address, default_limits=["600/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("SentinelleRx API starting (env=%s, keycloak=%s)",
             settings.environment, settings.keycloak_enabled)
    yield
    log.info("SentinelleRx API shutting down")


DESCRIPTION = """
**SentinelleRx** — plateforme nationale de prédiction des ruptures de médicaments.

Prévoit les tensions d'approvisionnement *avant* qu'elles n'atteignent les
patients, avec des recommandations **explicables** validées par des
professionnels de santé.

- 🔮 Prévision de la demande (XGBoost / LightGBM / Prophet)
- 🚨 Prédiction des ruptures (5 niveaux : vert → critique)
- 🧠 IA explicable (SHAP)
- 💊 Substitutions thérapeutiques (ATC / DDD)
- 🗺️ Command Center national, portail pharmacie, portail citoyen
"""

app = FastAPI(
    title="SentinelleRx API",
    version="0.1.0",
    description=DESCRIPTION,
    contact={"name": "SentinelleRx", "url": "https://sentinellerx.tn"},
    license_info={"name": "Proprietary"},
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Sondes de disponibilité"},
        {"name": "auth", "description": "Authentification et profil"},
        {"name": "medications", "description": "Catalogue et substitutions"},
        {"name": "stock", "description": "Stocks pharmacie et national"},
        {"name": "sales", "description": "Ventes et séries temporelles"},
        {"name": "forecasts", "description": "Prévisions de demande"},
        {"name": "shortages", "description": "Prédictions de rupture et carte"},
        {"name": "recommendations", "description": "Recommandations et validation"},
        {"name": "alerts", "description": "Alertes et notifications"},
        {"name": "pharmacies", "description": "Recherche de pharmacies (géolocalisée)"},
        {"name": "citizen", "description": "Recherche publique de disponibilité"},
        {"name": "admin", "description": "Administration et audit"},
    ],
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Trop de requêtes. Réessayez plus tard."})


setup_observability(app)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": "SentinelleRx API", "version": "0.1.0", "docs": "/docs"}
