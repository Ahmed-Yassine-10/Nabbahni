"""Unit tests for feature engineering, evaluation, and severity mapping."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.evaluation import wape
from ml.explain import explain_row
from ml.features import FEATURE_COLUMNS, build_series_features
from ml.shortage import SHORTAGE_FEATURES, severity_from_probability


def _fake_sales(days: int = 200) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    rows = []
    for mid in ["m1", "m2"]:
        for gid in ["g1"]:
            for i, d in enumerate(dates):
                rows.append({
                    "medication_id": mid, "governorate_id": gid, "date": d,
                    "quantity": int(50 + 10 * np.sin(i / 7) + (i * 0.05)),
                    "stockout": False,
                })
    return pd.DataFrame(rows)


def test_build_features_produces_targets():
    sales = _fake_sales()
    meds = pd.DataFrame({
        "medication_id": ["m1", "m2"], "unit_price_tnd": [5.0, 3.0],
        "is_essential": [True, False],
    })
    flu = pd.DataFrame({"date": sales["date"].unique(), "flu_index": 50.0})
    feats = build_series_features(sales, meds, flu, [7, 30])
    assert not feats.empty
    for col in FEATURE_COLUMNS:
        assert col in feats.columns
    assert "target_7" in feats.columns and "target_30" in feats.columns


def test_wape_perfect_prediction():
    y = np.array([10.0, 20.0, 30.0])
    assert wape(y, y) == 0.0


def test_severity_thresholds():
    assert severity_from_probability(0.9, 40, False) == "critical"
    assert severity_from_probability(0.5, 40, False) == "orange"
    assert severity_from_probability(0.1, 40, False) == "green"
    # Essential + very low cover overrides to critical.
    assert severity_from_probability(0.1, 3, True) == "critical"


def test_explain_row_narrative():
    values = np.array([20.0, 100.0, 5.0, 0.25, 0.1, 8.0, 6.0, 20.0, 65.0, 1.0])
    shap = np.array([0.3, -0.1, 0.05, 0.4, 0.2, 0.35, 0.1, 0.3, 0.15, 0.05])
    out = explain_row(SHORTAGE_FEATURES, values, shap)
    assert out["narrative_fr"].startswith("Risque de rupture élevé")
    assert len(out["top_factors"]) >= 1
