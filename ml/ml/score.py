"""Batch scoring: forecasts + shortage predictions + explanations + recommendations + alerts.

Run with:  python -m ml.score
Loads champion demand models and the shortage classifier, scores every
medication × governorate pair (plus national aggregates), and writes results in
a single refresh. Explanations are computed here (SHAP) so the API never does.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import delete

from app.core.cache import cache_invalidate
from app.core.database import SessionLocal
from app.core.enums import AlertScope, Severity
from app.models import (
    Alert,
    Forecast,
    Medication,
    PredictionExplanation,
    Recommendation,
    ShortagePrediction,
)
from app.services.recommendations import RecommendationContext, generate
from ml import data as dataio
from ml.config import HORIZONS
from ml.explain import explain_row, make_explainer, shap_for_matrix
from ml.features import FEATURE_COLUMNS, build_series_features
from ml.registry import load_local
from ml.shortage import SHORTAGE_FEATURES, severity_from_probability

logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ml.score")

_TREND_EPS = 0.05


def _trend(change: float) -> str:
    if change > _TREND_EPS:
        return "rising"
    if change < -_TREND_EPS:
        return "falling"
    return "stable"


def main() -> None:
    session = SessionLocal()
    today = date.today()

    log.info("Loading data + models…")
    sales = dataio.load_sales_by_gov()
    meds = dataio.load_medications()
    govs = dataio.load_governorates()
    flu = dataio.load_flu_index()
    cur_stock = dataio.load_current_stock()
    nat_stock = dataio.load_national_stock_latest()
    delays = dataio.load_supplier_delays()
    if sales.empty:
        raise SystemExit("No sales data. Run seed + train first.")

    champions = {h: load_local(f"demand-champion-{h}") for h in HORIZONS}
    if not any(champions.values()):
        raise SystemExit("No trained demand champions found. Run `make train` first.")
    shortage_model = load_local("shortage")

    meds_by_id = meds.set_index("medication_id").to_dict("index")
    stock_lookup = (
        cur_stock.set_index(["medication_id", "governorate_id"])["stock_qty"].to_dict()
        if not cur_stock.empty else {}
    )
    nat_stock_lookup = (
        nat_stock.set_index("medication_id")["national_stock"].to_dict()
        if not nat_stock.empty else {}
    )
    delay_lookup = delays.set_index("medication_id").to_dict("index") if not delays.empty else {}
    flu_latest = float(flu.sort_values("date")["flu_index"].iloc[-1]) if not flu.empty else 0.0

    # ── Demand forecasts from latest feature rows ──
    log.info("Building features + forecasting…")
    features = build_series_features(sales, meds, flu, HORIZONS)
    latest_rows = (
        features.dropna(subset=FEATURE_COLUMNS)
        .sort_values("date")
        .groupby(["medication_id", "governorate_id"], as_index=False)
        .tail(1)
    )

    session.execute(delete(Forecast))
    session.execute(delete(Recommendation))
    session.execute(delete(PredictionExplanation))
    session.execute(delete(ShortagePrediction))
    session.execute(delete(Alert))
    session.commit()

    forecast_objs: list[Forecast] = []
    # median 30d gov forecast used for coverage + national aggregation
    gov_daily_forecast: dict[tuple[str, str], float] = {}
    national_daily_forecast: dict[str, float] = {}

    X_latest = latest_rows[FEATURE_COLUMNS].astype(float)
    for h in HORIZONS:
        model = champions.get(h)
        if model is None:
            continue
        med_pred = model.models[0.5].predict(X_latest)
        lo = model.models[0.1].predict(X_latest)
        hi = model.models[0.9].predict(X_latest)
        for i, (_, row) in enumerate(latest_rows.iterrows()):
            mid, gid = row["medication_id"], row["governorate_id"]
            qty = max(0.0, float(med_pred[i]))
            forecast_objs.append(Forecast(
                medication_id=mid, governorate_id=gid, horizon_days=h, forecast_date=today,
                predicted_qty=round(qty, 2),
                ci_lower=round(max(0.0, float(lo[i])), 2),
                ci_upper=round(max(qty, float(hi[i])), 2),
                trend=_trend(float(row["demand_change_30d"])),
            ))
            if h == 30:
                gov_daily_forecast[(mid, gid)] = qty / 30.0
                national_daily_forecast[mid] = national_daily_forecast.get(mid, 0.0) + qty / 30.0

    # National forecasts (sum across governorates).
    nat_forecast_accum: dict[tuple[str, int], list[float]] = {}
    for f in forecast_objs:
        key = (f.medication_id, f.horizon_days)
        acc = nat_forecast_accum.setdefault(key, [0.0, 0.0, 0.0])
        acc[0] += float(f.predicted_qty)
        acc[1] += float(f.ci_lower)
        acc[2] += float(f.ci_upper)
    for (mid, h), (q, lo, hi) in nat_forecast_accum.items():
        forecast_objs.append(Forecast(
            medication_id=mid, governorate_id=None, horizon_days=h, forecast_date=today,
            predicted_qty=round(q, 2), ci_lower=round(lo, 2), ci_upper=round(hi, 2),
            trend="stable",
        ))
    session.bulk_save_objects(forecast_objs)
    session.commit()
    log.info("Forecasts written: %d", len(forecast_objs))

    # ── Shortage predictions + explanations ──
    log.info("Scoring shortage risk…")
    explainer = make_explainer(shortage_model.clf) if shortage_model else None

    # Precompute national 28d demand per medication for coverage.
    nat_demand = sales.groupby(["medication_id", "date"], as_index=False)["quantity"].sum()
    nat_daily_28 = (
        nat_demand.sort_values("date").groupby("medication_id")["quantity"]
        .apply(lambda s: s.tail(28).mean()).to_dict()
    )

    feature_rows: list[dict] = []
    meta: list[dict] = []
    for (mid, gid), grp in sales.groupby(["medication_id", "governorate_id"]):
        g = grp.sort_values("date")
        q = g["quantity"]
        demand_mean_28 = float(q.tail(28).mean())
        demand_std_28 = float(q.tail(28).std() or 0)
        recent = float(q.tail(7).mean())
        base = float(q.tail(37).head(7).mean() or recent)
        change = (recent - base) / base if base > 0 else 0.0
        hist_rate = float(g["stockout"].astype(float).tail(90).mean() or 0)
        nat_d = nat_daily_28.get(mid, demand_mean_28 * 24) or 1.0
        national_stock = float(nat_stock_lookup.get(mid, nat_d * 60))
        national_cov = min(national_stock / nat_d, 120.0) if nat_d > 0 else 120.0
        d = delay_lookup.get(mid, {})
        essential = float(meds_by_id.get(mid, {}).get("is_essential", 0))

        feature_rows.append({
            "coverage_proxy": national_cov,
            "demand_mean_28": demand_mean_28,
            "demand_std_28": demand_std_28,
            "demand_change_30d": change,
            "hist_stockout_rate_90": hist_rate,
            "supplier_delay_mean": float(d.get("supplier_delay_mean", 0)),
            "supplier_delay_std": float(d.get("supplier_delay_std", 0)),
            "national_coverage_days": national_cov,
            "flu_index": flu_latest,
            "is_essential": essential,
        })
        gov_stock = float(stock_lookup.get((mid, gid), 0))
        gov_daily = gov_daily_forecast.get((mid, gid), max(demand_mean_28, 0.1))
        coverage_days = gov_stock / gov_daily if gov_daily > 0 else 999.0
        meta.append({
            "mid": mid, "gid": gid, "coverage_days": coverage_days,
            "national_cov": national_cov, "national_stock": national_stock,
            "national_daily": nat_d, "essential": bool(essential),
        })

    X = pd.DataFrame(feature_rows)[SHORTAGE_FEATURES].astype(float)
    if shortage_model is not None and hasattr(shortage_model.clf, "predict_proba"):
        proba = shortage_model.clf.predict_proba(X.values)[:, 1]
    else:
        proba = np.zeros(len(X))

    shap_matrix = shap_for_matrix(explainer, X.values) if explainer is not None else None

    pred_objs: list[ShortagePrediction] = []
    expl_payloads: list[tuple[int, dict]] = []  # (index into pred_objs, payload)
    # Track worst per-med for national rows + recommendations.
    worst_by_med: dict[str, dict] = {}

    for i, m in enumerate(meta):
        p = float(proba[i])
        sev = severity_from_probability(p, m["coverage_days"], m["essential"])
        est_date = _estimate_date(m["coverage_days"])
        pred = ShortagePrediction(
            medication_id=m["mid"], governorate_id=m["gid"], horizon_days=30,
            probability=round(p, 4), severity=Severity(sev),
            estimated_shortage_date=est_date, coverage_days=round(m["coverage_days"], 2),
            computed_at=datetime.now(timezone.utc),
        )
        pred_objs.append(pred)

        payload = None
        if shap_matrix is not None:
            payload = explain_row(SHORTAGE_FEATURES, X.values[i], shap_matrix[i])
            expl_payloads.append((len(pred_objs) - 1, payload))

        cur = worst_by_med.get(m["mid"])
        if cur is None or Severity(sev) >= Severity(cur["severity"]):
            worst_by_med[m["mid"]] = {
                "severity": sev, "probability": p, "gid": m["gid"],
                "national_cov": m["national_cov"], "national_stock": m["national_stock"],
                "national_daily": m["national_daily"], "essential": m["essential"],
                "payload": payload,
            }

    # National (governorate_id NULL) rows = worst governorate per medication.
    for mid, w in worst_by_med.items():
        pred_objs.append(ShortagePrediction(
            medication_id=mid, governorate_id=None, horizon_days=30,
            probability=round(w["probability"], 4), severity=Severity(w["severity"]),
            estimated_shortage_date=_estimate_date(w["national_cov"]),
            coverage_days=round(w["national_cov"], 2),
            computed_at=datetime.now(timezone.utc),
        ))
        # Carry the driving governorate's SHAP payload onto the national row.
        # The national figure IS that governorate's case, so it has the same
        # explanation — and without this the medication detail page, which
        # reads the national row, would have no rationale to show at all.
        if w.get("payload") is not None:
            expl_payloads.append((len(pred_objs) - 1, w["payload"]))

    session.bulk_save_objects(pred_objs, return_defaults=True)
    session.flush()

    # Attach explanations (need prediction ids → bulk_save with return_defaults).
    expl_objs = []
    for idx, payload in expl_payloads:
        expl_objs.append(PredictionExplanation(
            shortage_prediction_id=pred_objs[idx].id,
            shap_values=payload["shap_values"], top_factors=payload["top_factors"],
            narrative_fr=payload["narrative_fr"], narrative_ar=payload["narrative_ar"],
        ))
    session.bulk_save_objects(expl_objs)
    session.commit()
    log.info("Shortage predictions: %d  (+%d explanations)", len(pred_objs), len(expl_objs))

    # ── Recommendations (from national worst per medication) ──
    rec_objs = _build_recommendations(worst_by_med, meds_by_id, national_daily_forecast)
    session.bulk_save_objects(rec_objs)

    # ── Alerts (severity >= orange) ──
    alert_objs = _build_alerts(pred_objs, meds_by_id)
    session.bulk_save_objects(alert_objs)
    session.commit()
    log.info("Recommendations: %d  Alerts: %d", len(rec_objs), len(alert_objs))

    cache_invalidate("*")
    session.close()
    log.info("✅ Scoring complete")


def _estimate_date(coverage_days: float) -> date | None:
    if coverage_days is None or coverage_days > 90:
        return None
    return date.today() + timedelta(days=int(max(0, coverage_days)))


def _build_recommendations(worst_by_med, meds_by_id, national_daily_forecast) -> list:
    out = []
    for mid, w in worst_by_med.items():
        sev = Severity(w["severity"])
        if sev < Severity.yellow:
            continue
        med = meds_by_id.get(mid, {})
        daily = national_daily_forecast.get(mid, w["national_daily"])
        ctx = RecommendationContext(
            medication_id=mid,
            brand_name=med.get("brand_name", "Médicament"),
            is_essential=bool(med.get("is_essential", False)),
            unit_price_tnd=float(med.get("unit_price_tnd", 0) or 0),
            severity=sev,
            probability=w["probability"],
            horizon_days=30,
            national_coverage_days=w["national_cov"],
            forecast_demand_horizon=daily * 30,
            national_stock_qty=w["national_stock"],
            in_transit_qty=0.0,
            data_completeness=0.9,
        )
        for draft in generate(ctx):
            out.append(Recommendation(
                medication_id=mid, governorate_id=None, rec_type=draft.rec_type,
                title_fr=draft.title_fr, detail_fr=draft.detail_fr,
                confidence=draft.confidence, financial_impact_tnd=draft.financial_impact_tnd,
                expected_shortage_reduction_pct=draft.expected_shortage_reduction_pct,
                suggested_quantity=draft.suggested_quantity,
            ))
    return out


def _build_alerts(pred_objs, meds_by_id) -> list:
    out = []
    for p in pred_objs:
        sev = p.severity if isinstance(p.severity, Severity) else Severity(p.severity)
        if sev < Severity.orange:
            continue
        med = meds_by_id.get(p.medication_id, {})
        brand = med.get("brand_name", "Médicament")
        scope = AlertScope.national if p.governorate_id is None else AlertScope.governorate
        out.append(Alert(
            scope=scope, governorate_id=p.governorate_id, medication_id=p.medication_id,
            severity=sev,
            title_fr=f"Risque de rupture ({sev.value}) : {brand}",
            body_fr=(
                f"Probabilité {float(p.probability):.0%}, couverture estimée "
                f"{float(p.coverage_days or 0):.0f} jours."
            ),
        ))
    return out


if __name__ == "__main__":
    main()
