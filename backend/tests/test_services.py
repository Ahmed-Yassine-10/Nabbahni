"""Unit tests for pure domain services (no DB required)."""
from __future__ import annotations

from app.core.enums import EquivalenceLevel, RecommendationType, Severity
from app.services.availability import availability_from_severity, availability_from_stock
from app.services.recommendations import RecommendationContext, generate
from app.services.substitution import MedLite, build_candidates


def test_severity_ordering():
    assert Severity.critical > Severity.red
    assert Severity.red >= Severity.orange
    assert not (Severity.green > Severity.yellow)


def test_availability_mapping():
    assert availability_from_severity(Severity.green).value == "available"
    assert availability_from_severity(Severity.critical).value == "shortage"
    assert availability_from_stock(0, 5).value == "shortage"
    assert availability_from_stock(3, 5).value == "tension"
    assert availability_from_stock(50, 5).value == "available"


def test_substitution_same_dci():
    meds = [
        MedLite("1", "J01CA04", "Amoxicilline", 1.5),
        MedLite("2", "J01CA04", "Amoxicilline", 1.5),
        MedLite("3", "J01CR02", "Amoxicilline/Clav", 1.5),
        MedLite("4", "C10AA05", "Atorvastatine", 0.02),
    ]
    cands = build_candidates(meds)
    # Amoxicilline 1 <-> 2 should be identical DCI.
    pair = [c for c in cands if c.source_id == "1" and c.target_id == "2"]
    assert pair and pair[0].equivalence == EquivalenceLevel.identical_dci
    # Statin (different ATC group) is never a candidate for amoxicilline.
    assert not any(c.source_id == "1" and c.target_id == "4" for c in cands)


def test_recommendation_emergency_for_critical():
    ctx = RecommendationContext(
        medication_id="m1", brand_name="Clamoxyl", is_essential=True,
        unit_price_tnd=6.5, severity=Severity.critical, probability=0.9,
        horizon_days=30, national_coverage_days=4, forecast_demand_horizon=10000,
        national_stock_qty=1000, in_transit_qty=0,
    )
    recs = generate(ctx)
    types = {r.rec_type for r in recs}
    assert RecommendationType.emergency_procurement in types
    # Deficit-based quantity should be positive and drive financial impact.
    emergency = next(r for r in recs if r.rec_type == RecommendationType.emergency_procurement)
    assert emergency.suggested_quantity and emergency.financial_impact_tnd > 0


def test_recommendation_none_for_green():
    ctx = RecommendationContext(
        medication_id="m2", brand_name="Doliprane", is_essential=False,
        unit_price_tnd=2.1, severity=Severity.green, probability=0.05,
        horizon_days=30, national_coverage_days=90, forecast_demand_horizon=100,
        national_stock_qty=100000, in_transit_qty=0,
    )
    assert generate(ctx) == []
