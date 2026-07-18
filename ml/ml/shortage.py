"""Shortage prediction engine.

A LightGBM binary classifier estimates the probability that a medication enters
a stockout in a governorate within the horizon. Training labels come from the
historical stockout flag (driven by injected shortage episodes). Probability is
mapped to the five-level severity scale, with a safety override that forces
`critical` when an essential medication has < 5 days of cover.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

log = logging.getLogger("ml.shortage")

SHORTAGE_FEATURES = [
    "coverage_proxy",
    "demand_mean_28",
    "demand_std_28",
    "demand_change_30d",
    "hist_stockout_rate_90",
    "supplier_delay_mean",
    "supplier_delay_std",
    "national_coverage_days",
    "flu_index",
    "is_essential",
]

# Probability thresholds → severity.
_THRESHOLDS = [
    (0.80, "critical"),
    (0.60, "red"),
    (0.40, "orange"),
    (0.20, "yellow"),
    (0.0, "green"),
]


def severity_from_probability(prob: float, coverage_days: float | None,
                              is_essential: bool) -> str:
    for thresh, label in _THRESHOLDS:
        if prob >= thresh:
            severity = label
            break
    else:
        severity = "green"
    # Safety override: essential med running critically low is always critical.
    if is_essential and coverage_days is not None and coverage_days < 5:
        return "critical"
    return severity


@dataclass
class ShortageModel:
    clf: object
    features: list[str] = field(default_factory=lambda: list(SHORTAGE_FEATURES))
    metrics: dict = field(default_factory=dict)


def build_training_table(
    sales: pd.DataFrame,
    meds: pd.DataFrame,
    national_hist: pd.DataFrame,
    supplier_delays: pd.DataFrame,
    flu: pd.DataFrame,
    horizon: int = 30,
    sample_every: int = 7,
) -> pd.DataFrame:
    """Construct a supervised table for the stockout classifier."""
    if sales.empty:
        return pd.DataFrame()

    # National daily demand per medication (for coverage proxy).
    nat_demand = sales.groupby(["medication_id", "date"], as_index=False)["quantity"].sum()
    nat_demand = nat_demand.rename(columns={"quantity": "nat_demand"})
    nat_demand["nat_demand_28"] = (
        nat_demand.groupby("medication_id")["nat_demand"]
        .transform(lambda s: s.rolling(28, min_periods=5).mean())
    )

    flu_idx = flu.set_index("date")["flu_index"] if not flu.empty else None
    delay_map = supplier_delays.set_index("medication_id") if not supplier_delays.empty else None
    essential_map = meds.set_index("medication_id")["is_essential"].to_dict()

    # National stock forward-filled to daily per medication.
    nat_stock_daily = {}
    if not national_hist.empty:
        for mid, grp in national_hist.groupby("medication_id"):
            s = grp.set_index("recorded_at")["quantity"].sort_index()
            nat_stock_daily[mid] = s

    rows = []
    for (mid, gid), grp in sales.groupby(["medication_id", "governorate_id"]):
        g = grp.sort_values("date").reset_index(drop=True)
        g["demand_mean_28"] = g["quantity"].rolling(28, min_periods=5).mean()
        g["demand_std_28"] = g["quantity"].rolling(28, min_periods=5).std()
        base = g["quantity"].shift(30).rolling(7, min_periods=2).mean()
        recent = g["quantity"].rolling(7, min_periods=2).mean()
        g["demand_change_30d"] = ((recent - base) / base.replace(0, np.nan)).fillna(0)
        g["hist_stockout_rate_90"] = g["stockout"].astype(float).rolling(90, min_periods=10).mean()
        # Label: stockout occurs within the next `horizon` days.
        g["future_stockout"] = (
            g["stockout"].astype(int)[::-1].rolling(horizon, min_periods=1).max()[::-1]
        ).shift(-1).fillna(0)

        nat_series = nat_demand[nat_demand["medication_id"] == mid].set_index("date")
        essential = float(essential_map.get(mid, 0))
        d_mean = float(delay_map.loc[mid, "supplier_delay_mean"]) if (
            delay_map is not None and mid in delay_map.index) else 0.0
        d_std = float(delay_map.loc[mid, "supplier_delay_std"]) if (
            delay_map is not None and mid in delay_map.index) else 0.0
        stock_series = nat_stock_daily.get(mid)

        for i in range(0, len(g), sample_every):
            row = g.iloc[i]
            day = row["date"]
            if pd.isna(row["demand_mean_28"]) or pd.isna(row["hist_stockout_rate_90"]):
                continue
            nat_dem_28 = nat_series["nat_demand_28"].get(day, np.nan)
            if stock_series is not None and len(stock_series):
                pos = stock_series.index.searchsorted(day, side="right") - 1
                nat_stock = float(stock_series.iloc[max(0, pos)])
            else:
                nat_stock = np.nan
            national_coverage = (
                nat_stock / nat_dem_28 if nat_dem_28 and nat_dem_28 > 0 and not np.isnan(nat_stock)
                else 60.0
            )
            gov_daily = max(row["demand_mean_28"], 0.1)
            coverage_proxy = min(national_coverage, 120.0)
            flu_val = float(flu_idx.get(day, 0)) if flu_idx is not None else 0.0
            rows.append({
                "medication_id": mid, "governorate_id": gid, "date": day,
                "coverage_proxy": coverage_proxy,
                "demand_mean_28": float(row["demand_mean_28"]),
                "demand_std_28": float(row["demand_std_28"] or 0),
                "demand_change_30d": float(row["demand_change_30d"]),
                "hist_stockout_rate_90": float(row["hist_stockout_rate_90"]),
                "supplier_delay_mean": d_mean,
                "supplier_delay_std": d_std,
                "national_coverage_days": float(min(national_coverage, 120.0)),
                "flu_index": flu_val,
                "is_essential": essential,
                "gov_daily_demand": gov_daily,
                "label": int(row["future_stockout"]),
            })
    return pd.DataFrame(rows)


def train_classifier(table: pd.DataFrame) -> ShortageModel:
    from lightgbm import LGBMClassifier
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    X = table[SHORTAGE_FEATURES].astype(float)
    y = table["label"].astype(int)

    if y.nunique() < 2:
        log.warning("Only one class present in shortage labels; using a constant model")
        clf = LGBMClassifier(n_estimators=10, verbose=-1).fit(X, y)
        return ShortageModel(clf=clf, metrics={"auc": float("nan"), "ap": float("nan")})

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    pos_weight = (y_tr == 0).sum() / max(1, (y_tr == 1).sum())
    clf = LGBMClassifier(
        n_estimators=400, num_leaves=48, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, class_weight=None,
        scale_pos_weight=pos_weight, random_state=42, verbose=-1,
    ).fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    metrics = {
        "auc": float(roc_auc_score(y_te, proba)),
        "ap": float(average_precision_score(y_te, proba)),
        "positives": int(y.sum()),
        "n_train": int(len(table)),
    }
    log.info("Shortage classifier  AUC=%.3f  AP=%.3f  pos=%d",
             metrics["auc"], metrics["ap"], metrics["positives"])
    return ShortageModel(clf=clf, metrics=metrics)
