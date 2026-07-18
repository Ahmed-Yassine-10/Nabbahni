"""Entity read/write schemas used across API routers."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.enums import (
    AlertScope,
    AvailabilityStatus,
    EquivalenceLevel,
    PharmacyType,
    RecommendationStatus,
    RecommendationType,
    Severity,
    Trend,
)
from app.schemas.common import ORMModel


# ---- Medications ----
class MedicationOut(ORMModel):
    id: uuid.UUID
    atc_code: str
    dci: str
    brand_name: str
    form: str
    dosage: str
    unit: str
    ddd_value: float | None = None
    ddd_unit: str | None = None
    unit_price_tnd: float
    is_essential: bool
    requires_prescription: bool


class MedicationBrief(ORMModel):
    """Minimal medication identity, embedded in list payloads.

    Lists are read far more often than medication detail, and rendering a row
    as a bare UUID is useless — so every list endpoint carries this.
    """

    id: uuid.UUID
    brand_name: str
    dci: str
    atc_code: str
    form: str
    dosage: str
    is_essential: bool
    unit_price_tnd: float


# ---- Geography / actors ----
class GovernorateOut(ORMModel):
    id: uuid.UUID
    code: str
    name_fr: str
    name_ar: str
    population: int
    centroid_lat: float
    centroid_lon: float


class PharmacyOut(ORMModel):
    id: uuid.UUID
    name: str
    type: PharmacyType
    governorate_id: uuid.UUID
    address: str | None = None
    phone: str | None = None
    on_call: bool


class PharmacyNearby(BaseModel):
    id: uuid.UUID
    name: str
    type: PharmacyType
    address: str | None
    phone: str | None
    distance_km: float
    latitude: float
    longitude: float
    availability: AvailabilityStatus
    quantity: int | None = None


# ---- Stock / sales ----
class StockOut(ORMModel):
    id: uuid.UUID
    pharmacy_id: uuid.UUID
    medication_id: uuid.UUID
    quantity: int
    min_threshold: int
    recorded_at: date
    medication: MedicationBrief | None = None
    # Days of cover implied by this pharmacy's recent consumption.
    coverage_days: float | None = None


class StockIngestItem(BaseModel):
    medication_id: uuid.UUID
    quantity: int = Field(ge=0)
    min_threshold: int = Field(default=0, ge=0)
    recorded_at: date | None = None


class StockIngestRequest(BaseModel):
    items: list[StockIngestItem]


class NationalStockOut(BaseModel):
    medication_id: uuid.UUID
    brand_name: str
    dci: str
    quantity: int
    coverage_days: float | None = None
    recorded_at: date
    is_essential: bool = False
    unit_price_tnd: float = 0.0


class StockAnalysisBucket(BaseModel):
    """One band of the national coverage-days distribution."""

    label: str
    min_days: float
    max_days: float | None
    count: int
    severity: Severity


class StockAnalysisOut(BaseModel):
    total_medications: int
    total_units: int
    total_value_tnd: float
    median_coverage_days: float
    essential_at_risk: int
    buckets: list[StockAnalysisBucket]
    lowest_coverage: list[NationalStockOut]


class SalesPoint(BaseModel):
    date: date
    quantity: int
    revenue_tnd: float


class SalesIngestItem(BaseModel):
    pharmacy_id: uuid.UUID
    medication_id: uuid.UUID
    date: date
    quantity: int = Field(ge=0)
    revenue_tnd: float = Field(default=0, ge=0)


class SalesIngestRequest(BaseModel):
    items: list[SalesIngestItem]


# ---- Forecasts ----
class ForecastOut(ORMModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    governorate_id: uuid.UUID | None
    horizon_days: int
    forecast_date: date
    predicted_qty: float
    ci_lower: float
    ci_upper: float
    trend: Trend


# ---- Shortages ----
class TopFactor(BaseModel):
    feature: str
    value: float
    shap: float
    label_fr: str


class ExplanationOut(ORMModel):
    top_factors: list[TopFactor] = []
    narrative_fr: str | None = None
    narrative_ar: str | None = None


class ShortageOut(ORMModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    governorate_id: uuid.UUID | None
    horizon_days: int
    probability: float
    severity: Severity
    estimated_shortage_date: date | None
    coverage_days: float | None
    computed_at: datetime
    # Denormalized labels so clients can render a readable row without an
    # extra lookup per record. Populated by the list/detail endpoints.
    medication: MedicationBrief | None = None
    governorate_name: str | None = None


class ShortageDetail(ShortageOut):
    medication: MedicationOut | None = None
    explanation: ExplanationOut | None = None


# ---- Recommendations ----
class RecommendationOut(ORMModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    governorate_id: uuid.UUID | None
    rec_type: RecommendationType
    title_fr: str
    detail_fr: str
    confidence: float
    financial_impact_tnd: float
    expected_shortage_reduction_pct: float
    suggested_quantity: int | None
    status: RecommendationStatus
    validated_at: datetime | None
    medication: MedicationBrief | None = None
    governorate_name: str | None = None


# ---- Substitutions ----
class SubstitutionOut(BaseModel):
    id: uuid.UUID
    target: MedicationOut
    atc_match_level: int
    equivalence: EquivalenceLevel
    ddd_ratio: float | None
    notes_fr: str | None
    requires_pharmacist_validation: bool


# ---- Alerts ----
class AlertOut(ORMModel):
    id: uuid.UUID
    scope: AlertScope
    governorate_id: uuid.UUID | None
    pharmacy_id: uuid.UUID | None
    medication_id: uuid.UUID | None
    severity: Severity
    title_fr: str
    body_fr: str
    created_at: datetime
    acknowledged_at: datetime | None
    medication: MedicationBrief | None = None
    governorate_name: str | None = None


# ---- Citizen ----
class CitizenAvailabilityRow(BaseModel):
    governorate: str
    availability: AvailabilityStatus
    pharmacies_with_stock: int
    total_pharmacies: int


class CitizenAvailabilityOut(BaseModel):
    medication: MedicationOut
    national_status: AvailabilityStatus
    by_governorate: list[CitizenAvailabilityRow]
    alternatives: list[SubstitutionOut] = []


# ---- Me ----
class MeOut(BaseModel):
    sub: str
    email: str | None
    roles: list[str]
    pharmacy_id: uuid.UUID | None = None
    governorate_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
