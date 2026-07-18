"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    alerts,
    auth,
    citizen,
    expiry,
    forecasts,
    health,
    medications,
    pharmacies,
    recommendations,
    sales,
    shortages,
    stock,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/api/v1", tags=["auth"])
api_router.include_router(medications.router, prefix="/api/v1", tags=["medications"])
api_router.include_router(stock.router, prefix="/api/v1", tags=["stock"])
api_router.include_router(sales.router, prefix="/api/v1", tags=["sales"])
api_router.include_router(forecasts.router, prefix="/api/v1", tags=["forecasts"])
api_router.include_router(shortages.router, prefix="/api/v1", tags=["shortages"])
api_router.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])
api_router.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
api_router.include_router(expiry.router, prefix="/api/v1", tags=["expiry"])
api_router.include_router(pharmacies.router, prefix="/api/v1", tags=["pharmacies"])
api_router.include_router(citizen.router, prefix="/api/v1", tags=["citizen"])
api_router.include_router(admin.router, prefix="/api/v1", tags=["admin"])
