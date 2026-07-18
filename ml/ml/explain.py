"""Explainability: SHAP values → human-readable French / Arabic rationale.

Explanations are computed at scoring time and persisted, so the request path
never runs SHAP. Each top contributing feature is rendered into a plain-language
sentence with its sign and magnitude, e.g. "La demande a augmenté de 21%".
"""
from __future__ import annotations

import numpy as np


def _pct(x: float) -> str:
    return f"{abs(x) * 100:.0f}%"


def _render_fr(feature: str, value: float, shap: float) -> str | None:
    """Return a French sentence for a feature that pushes risk up (shap > 0)."""
    if feature == "demand_change_30d" and value > 0.05:
        return f"La demande a augmenté de {_pct(value)} sur 30 jours"
    if feature in ("national_coverage_days", "coverage_proxy") and value < 30:
        return f"Couverture nationale faible ({value:.0f} jours de stock)"
    if feature == "supplier_delay_mean" and value > 3:
        return f"Fournisseur en retard de {value:.0f} jours en moyenne"
    if feature == "supplier_delay_std" and value > 5:
        return "Délais fournisseurs très irréguliers"
    if feature == "hist_stockout_rate_90" and value > 0.05:
        return f"Ruptures fréquentes récemment ({_pct(value)} des jours)"
    if feature == "demand_std_28" and shap > 0:
        return "Demande volatile difficile à couvrir"
    if feature == "flu_index" and value > 60:
        return "Saison épidémique active (grippe)"
    if feature == "is_essential" and value >= 1:
        return "Médicament essentiel (priorité élevée)"
    if feature == "demand_mean_28" and shap > 0:
        return "Niveau de consommation élevé"
    return None


def _render_ar(feature: str, value: float) -> str | None:
    mapping = {
        "demand_change_30d": "ارتفاع الطلب خلال 30 يومًا",
        "national_coverage_days": "تغطية وطنية منخفضة",
        "coverage_proxy": "تغطية وطنية منخفضة",
        "supplier_delay_mean": "تأخر المورّد",
        "hist_stockout_rate_90": "انقطاعات متكررة مؤخرًا",
        "flu_index": "موسم وبائي نشط",
        "is_essential": "دواء أساسي",
    }
    return mapping.get(feature)


def explain_row(
    feature_names: list[str],
    values: np.ndarray,
    shap_values: np.ndarray,
    top_k: int = 5,
) -> dict:
    """Build the stored explanation payload for a single prediction."""
    order = np.argsort(np.abs(shap_values))[::-1]
    top_factors = []
    narrative_bits_fr = []
    narrative_bits_ar = []
    seen_labels: set[str] = set()

    for idx in order[: top_k * 2]:
        feat = feature_names[idx]
        val = float(values[idx])
        shp = float(shap_values[idx])
        label = _render_fr(feat, val, shp)
        if label is None or label in seen_labels:
            continue  # skip factors that render an identical sentence
        seen_labels.add(label)
        top_factors.append({
            "feature": feat, "value": round(val, 3), "shap": round(shp, 4), "label_fr": label,
        })
        narrative_bits_fr.append(label)
        ar = _render_ar(feat, val)
        if ar:
            narrative_bits_ar.append(ar)
        if len(top_factors) >= top_k:
            break

    narrative_fr = (
        "Risque de rupture élevé car : " + " ; ".join(narrative_bits_fr) + "."
        if narrative_bits_fr else "Aucun facteur de risque déterminant identifié."
    )
    narrative_ar = (
        "خطر انقطاع مرتفع بسبب: " + "، ".join(narrative_bits_ar) + "."
        if narrative_bits_ar else "لا توجد عوامل خطر حاسمة."
    )
    shap_map = {feature_names[i]: round(float(shap_values[i]), 4) for i in range(len(feature_names))}
    return {
        "top_factors": top_factors,
        "shap_values": shap_map,
        "narrative_fr": narrative_fr,
        "narrative_ar": narrative_ar,
    }


def make_explainer(clf):
    """Return a SHAP TreeExplainer, or None if SHAP is unavailable."""
    try:
        import shap

        return shap.TreeExplainer(clf)
    except Exception:  # pragma: no cover
        return None


def shap_for_matrix(explainer, X: np.ndarray) -> np.ndarray:
    """Return SHAP values for the positive class as a 2D array (rows × features)."""
    vals = explainer.shap_values(X)
    if isinstance(vals, list):
        # Binary classifier: take the positive class contribution.
        vals = vals[1] if len(vals) > 1 else vals[0]
    return np.asarray(vals)
