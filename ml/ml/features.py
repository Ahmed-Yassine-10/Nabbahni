"""Feature engineering for demand forecasting.

Builds a supervised table from the medication × governorate daily series with
lag / rolling / calendar / external features and a forward-looking demand target
per horizon. Stockout days are demand-censored, so we impute a corrected demand
from the trailing average before computing targets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = [1, 7, 14, 28]
ROLL_WINDOWS = [7, 28, 90]

FEATURE_COLUMNS = [
    "lag_1", "lag_7", "lag_14", "lag_28",
    "roll_mean_7", "roll_mean_28", "roll_mean_90",
    "roll_std_7", "roll_std_28",
    "dow", "month", "is_weekend",
    "flu_index", "unit_price_tnd", "is_essential",
    "demand_change_30d",
]


def _impute_censored(df: pd.DataFrame) -> pd.DataFrame:
    """Replace stockout-day quantities with a trailing average (true demand proxy)."""
    df = df.sort_values("date").copy()
    trailing = df["quantity"].rolling(14, min_periods=3).mean()
    corrected = df["quantity"].where(~df["stockout"].astype(bool), trailing)
    df["demand"] = corrected.fillna(df["quantity"]).clip(lower=0)
    return df


def build_series_features(
    sales: pd.DataFrame,
    meds: pd.DataFrame,
    flu: pd.DataFrame,
    horizons: list[int],
) -> pd.DataFrame:
    """Return a long feature table with one target column per horizon."""
    if sales.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    flu_indexed = flu.set_index("date")["flu_index"] if not flu.empty else None

    for (mid, gid), grp in sales.groupby(["medication_id", "governorate_id"]):
        g = grp.sort_values("date").copy()
        # Reindex to a continuous daily calendar so lags are well defined.
        full_idx = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        g = g.set_index("date").reindex(full_idx)
        g["medication_id"] = mid
        g["governorate_id"] = gid
        g["quantity"] = g["quantity"].fillna(0)
        g["stockout"] = g["stockout"].fillna(False)
        g = g.rename_axis("date").reset_index()
        g = _impute_censored(g)

        for lag in LAGS:
            g[f"lag_{lag}"] = g["demand"].shift(lag)
        for w in ROLL_WINDOWS:
            g[f"roll_mean_{w}"] = g["demand"].shift(1).rolling(w, min_periods=2).mean()
        for w in [7, 28]:
            g[f"roll_std_{w}"] = g["demand"].shift(1).rolling(w, min_periods=2).std()

        g["dow"] = g["date"].dt.dayofweek
        g["month"] = g["date"].dt.month
        g["is_weekend"] = (g["dow"] >= 5).astype(int)

        # 30-day demand change ratio (drives the "demand rising" explanation).
        base_30 = g["demand"].shift(30).rolling(7, min_periods=2).mean()
        recent = g["demand"].shift(1).rolling(7, min_periods=2).mean()
        g["demand_change_30d"] = ((recent - base_30) / base_30.replace(0, np.nan)).fillna(0)

        if flu_indexed is not None:
            g["flu_index"] = g["date"].map(flu_indexed).ffill().bfill().fillna(0)
        else:
            g["flu_index"] = 0.0

        # Forward targets: total demand over the next h days.
        for h in horizons:
            g[f"target_{h}"] = (
                g["demand"].shift(-1).rolling(h, min_periods=1).sum().shift(-(h - 1))
            )
        frames.append(g)

    out = pd.concat(frames, ignore_index=True)
    out = out.merge(
        meds[["medication_id", "unit_price_tnd", "is_essential"]], on="medication_id", how="left"
    )
    out["unit_price_tnd"] = out["unit_price_tnd"].astype(float).fillna(0)
    out["is_essential"] = out["is_essential"].astype(float).fillna(0)
    return out


def training_frame(features: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    """Drop rows lacking features/target for a given horizon."""
    cols = FEATURE_COLUMNS
    target = f"target_{horizon}"
    df = features.dropna(subset=cols + [target]).copy()
    return df[cols + ["date", "medication_id", "governorate_id"]], df[target]
