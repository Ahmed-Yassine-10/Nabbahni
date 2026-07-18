"""Deterministic recommendation rules engine.

Given a scored shortage prediction plus supporting context, produce concrete,
explainable procurement recommendations. Rules are intentionally transparent —
the platform is decision-support, and a PCT officer validates every action.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.enums import RecommendationType, Severity


@dataclass
class RecommendationContext:
    medication_id: str
    brand_name: str
    is_essential: bool
    unit_price_tnd: float
    severity: Severity
    probability: float
    horizon_days: int
    national_coverage_days: float
    forecast_demand_horizon: float          # total predicted demand over the horizon
    national_stock_qty: float
    in_transit_qty: float
    governorate_id: str | None = None
    regional_coverage_ratio: float = 1.0    # max/min governorate coverage
    data_completeness: float = 1.0          # 0..1 fraction of expected inputs present


@dataclass
class DraftRecommendation:
    rec_type: RecommendationType
    title_fr: str
    detail_fr: str
    confidence: float
    financial_impact_tnd: float
    expected_shortage_reduction_pct: float
    suggested_quantity: int | None


_SAFETY_FACTOR = 1.2


def _deficit_quantity(ctx: RecommendationContext) -> int:
    """Units required to cover forecast demand over the horizon, with safety stock.

    For severe regional tensions where national stock is technically sufficient,
    fall back to a floor (~25% of horizon demand) so procurement/redistribution
    actions carry a meaningful, non-zero quantity.
    """
    available = ctx.national_stock_qty + ctx.in_transit_qty
    deficit = ctx.forecast_demand_horizon * _SAFETY_FACTOR - available
    qty = max(0, math.ceil(deficit))
    if qty == 0 and ctx.severity >= Severity.red:
        qty = math.ceil(ctx.forecast_demand_horizon * 0.25)
    return qty


def _confidence(ctx: RecommendationContext, base: float) -> float:
    return round(min(0.99, base * (0.6 + 0.4 * ctx.data_completeness)), 3)


def generate(ctx: RecommendationContext) -> list[DraftRecommendation]:
    recs: list[DraftRecommendation] = []
    qty = _deficit_quantity(ctx)
    cost = round(qty * ctx.unit_price_tnd, 2)

    # Rule 1 — emergency procurement for critical severity.
    if ctx.severity == Severity.critical:
        recs.append(
            DraftRecommendation(
                rec_type=RecommendationType.emergency_procurement,
                title_fr=f"Procédure d'urgence : {ctx.brand_name}",
                detail_fr=(
                    f"Risque critique (probabilité {ctx.probability:.0%}). Couverture "
                    f"nationale estimée à {ctx.national_coverage_days:.0f} jours. Déclencher "
                    f"un appel d'offres d'urgence pour ~{qty} unités."
                ),
                confidence=_confidence(ctx, 0.9),
                financial_impact_tnd=cost,
                expected_shortage_reduction_pct=75.0,
                suggested_quantity=qty,
            )
        )

    # Rule 2 — increase imports for severe risk + low national coverage.
    if ctx.severity >= Severity.red and ctx.national_coverage_days < 30 and qty > 0:
        recs.append(
            DraftRecommendation(
                rec_type=RecommendationType.increase_import,
                title_fr=f"Augmenter les importations : {ctx.brand_name}",
                detail_fr=(
                    f"La couverture nationale ({ctx.national_coverage_days:.0f} j) est "
                    f"inférieure au seuil de 30 jours. Commander ~{qty} unités "
                    f"(coût estimé {cost:,.0f} TND) pour absorber la demande prévue."
                ),
                confidence=_confidence(ctx, 0.82),
                financial_impact_tnd=cost,
                expected_shortage_reduction_pct=60.0,
                suggested_quantity=qty,
            )
        )

    # Rule 3 — redistribute when regional imbalance is high.
    if ctx.regional_coverage_ratio > 3.0 and ctx.severity >= Severity.orange:
        recs.append(
            DraftRecommendation(
                rec_type=RecommendationType.redistribute,
                title_fr=f"Redistribuer les stocks régionaux : {ctx.brand_name}",
                detail_fr=(
                    f"Déséquilibre régional détecté (ratio de couverture "
                    f"{ctx.regional_coverage_ratio:.1f}×). Transférer les stocks des "
                    f"gouvernorats excédentaires vers les zones en tension."
                ),
                confidence=_confidence(ctx, 0.7),
                financial_impact_tnd=round(cost * 0.15, 2),  # logistics-only cost
                expected_shortage_reduction_pct=35.0,
                suggested_quantity=None,
            )
        )

    # Rule 4 — prioritize hospitals for essential meds under pressure.
    if ctx.is_essential and ctx.severity >= Severity.orange:
        recs.append(
            DraftRecommendation(
                rec_type=RecommendationType.prioritize_hospitals,
                title_fr=f"Prioriser les hôpitaux : {ctx.brand_name}",
                detail_fr=(
                    "Médicament essentiel en tension. Réserver l'allocation prioritaire "
                    "aux pharmacies hospitalières jusqu'à stabilisation de "
                    "l'approvisionnement."
                ),
                confidence=_confidence(ctx, 0.75),
                financial_impact_tnd=0.0,
                expected_shortage_reduction_pct=20.0,
                suggested_quantity=None,
            )
        )

    # Fallback — mild risk still worth a nudge on ordering cadence.
    if not recs and ctx.severity >= Severity.yellow and qty > 0:
        recs.append(
            DraftRecommendation(
                rec_type=RecommendationType.adjust_order,
                title_fr=f"Ajuster les commandes : {ctx.brand_name}",
                detail_fr=(
                    f"Tendance de demande à surveiller. Anticiper une commande "
                    f"d'environ {qty} unités pour maintenir la couverture."
                ),
                confidence=_confidence(ctx, 0.6),
                financial_impact_tnd=cost,
                expected_shortage_reduction_pct=15.0,
                suggested_quantity=qty,
            )
        )

    return recs
