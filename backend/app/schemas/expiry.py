"""Schemas for expiry risk, allocation and redistribution."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.core.enums import Severity


class ExpiryBandOut(BaseModel):
    label: str
    min_days: int | None
    max_days: int | None
    severity: Severity
    units: int
    value_tnd: float


class BatchRiskOut(BaseModel):
    """One lot, with how much of it is projected to expire unsold."""

    batch_id: str
    medication_id: str
    brand_name: str
    dci: str
    pharmacy_id: str | None
    pharmacy_name: str | None
    lot_number: str
    quantity: int
    expiry_date: date
    days_to_expiry: int
    daily_rate: float
    projected_consumption: int
    at_risk_quantity: int
    at_risk_value_tnd: float
    severity: Severity


class ExpiryAnalysisOut(BaseModel):
    total_units: int
    total_value_tnd: float
    at_risk_units: int
    at_risk_value_tnd: float
    expired_units: int
    expired_value_tnd: float
    waste_rate_pct: float
    bands: list[ExpiryBandOut]
    worst_batches: list[BatchRiskOut]


class AllocationOut(BaseModel):
    """How much of one medication a pharmacy should actually receive."""

    medication_id: str
    brand_name: str
    dci: str
    is_essential: bool
    daily_rate: float
    current_stock: int
    usable_stock: int
    target_stock: int
    recommended_quantity: int
    surplus_quantity: int
    cover_days_after: float | None
    at_risk_quantity: int
    at_risk_value_tnd: float
    order_value_tnd: float
    reason: str


class PharmacyExpiryOut(BaseModel):
    pharmacy_id: str
    pharmacy_name: str
    at_risk_units: int
    at_risk_value_tnd: float
    order_value_tnd: float
    batches: list[BatchRiskOut]
    allocations: list[AllocationOut]


class TransferOut(BaseModel):
    medication_id: str
    brand_name: str
    from_pharmacy_id: str
    from_pharmacy_name: str
    to_pharmacy_id: str
    to_pharmacy_name: str
    quantity: int
    expiry_date: date
    days_to_expiry: int
    value_saved_tnd: float
    rationale: str
