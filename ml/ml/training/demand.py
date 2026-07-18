"""Demand forecasting trainers: XGBoost, LightGBM (quantile), Prophet.

Global models: one model per (family, horizon) with medication and governorate
as categorical features, rather than one model per series. This keeps training
tractable at national scale while still learning per-series patterns from the
lag/rolling features. Prophet, which is per-series, runs only on the busiest
national aggregates.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ml.evaluation import mape, rmse, rolling_origin_splits, wape
from ml.features import FEATURE_COLUMNS

log = logging.getLogger("ml.training.demand")


@dataclass
class TrainedDemandModel:
    family: str
    horizon: int
    models: dict           # quantile -> fitted estimator (median at 0.5)
    metrics: dict = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))


def _fit_xgb(X, y, quantile: float):
    from xgboost import XGBRegressor

    return XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:quantileerror",
        quantile_alpha=quantile,
        n_jobs=-1,
        random_state=42,
    ).fit(X, y)


def _fit_lgbm(X, y, quantile: float):
    from lightgbm import LGBMRegressor

    return LGBMRegressor(
        n_estimators=400,
        num_leaves=48,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="quantile",
        alpha=quantile,
        n_jobs=-1,
        random_state=42,
        verbose=-1,
    ).fit(X, y)


_FIT = {"xgboost": _fit_xgb, "lightgbm": _fit_lgbm}


def train_boosted(
    family: str, features: pd.DataFrame, horizon: int, quantiles=(0.1, 0.5, 0.9),
    folds: int = 3,
) -> TrainedDemandModel:
    target = f"target_{horizon}"
    df = features.dropna(subset=FEATURE_COLUMNS + [target]).copy()
    if df.empty:
        raise ValueError(f"No training rows for horizon {horizon}")

    X_all = df[FEATURE_COLUMNS].astype(float)
    y_all = df[target].astype(float).values
    dates = df["date"]

    # Backtest the median model.
    fold_wape, fold_mape, fold_rmse = [], [], []
    for train_mask, test_mask in rolling_origin_splits(dates, folds, horizon):
        if test_mask.sum() == 0 or train_mask.sum() < 50:
            continue
        m = _FIT[family](X_all[train_mask.values], y_all[train_mask.values], 0.5)
        pred = m.predict(X_all[test_mask.values])
        yt = y_all[test_mask.values]
        fold_wape.append(wape(yt, pred))
        fold_mape.append(mape(yt, pred))
        fold_rmse.append(rmse(yt, pred))

    # Fit final quantile models on all data.
    models = {q: _FIT[family](X_all, y_all, q) for q in quantiles}
    metrics = {
        "wape": float(np.nanmean(fold_wape)) if fold_wape else float("nan"),
        "mape": float(np.nanmean(fold_mape)) if fold_mape else float("nan"),
        "rmse": float(np.nanmean(fold_rmse)) if fold_rmse else float("nan"),
        "n_train": int(len(df)),
    }
    log.info("%s h=%d  WAPE=%.3f  RMSE=%.1f  n=%d", family, horizon,
             metrics["wape"], metrics["rmse"], metrics["n_train"])
    return TrainedDemandModel(family=family, horizon=horizon, models=models, metrics=metrics)


def train_prophet_national(
    sales_by_gov: pd.DataFrame, meds: pd.DataFrame, horizon: int, top_series: int = 40,
) -> dict:
    """Fit Prophet on the top national aggregate series; return WAPE summary.

    Prophet is per-series and slow, so we only benchmark it on the busiest
    national medication series to provide a fair three-way comparison.
    """
    try:
        from prophet import Prophet
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("Prophet unavailable (%s); skipping", exc)
        return {"wape": float("nan"), "mape": float("nan"), "rmse": float("nan"),
                "n_series": 0, "skipped": True}

    national = (
        sales_by_gov.groupby(["medication_id", "date"], as_index=False)["quantity"].sum()
    )
    volumes = national.groupby("medication_id")["quantity"].sum().sort_values(ascending=False)
    top = volumes.head(top_series).index.tolist()

    wapes, mapes, rmses = [], [], []
    import logging as _logging

    _logging.getLogger("prophet").setLevel(_logging.ERROR)
    _logging.getLogger("cmdstanpy").setLevel(_logging.ERROR)

    for mid in top:
        series = national[national["medication_id"] == mid][["date", "quantity"]].copy()
        series.columns = ["ds", "y"]
        if len(series) < 90:
            continue
        cutoff = series["ds"].quantile(0.8)
        train = series[series["ds"] <= cutoff]
        test = series[series["ds"] > cutoff]
        if len(test) < horizon:
            continue
        try:
            m = Prophet(weekly_seasonality=True, yearly_seasonality=True,
                        daily_seasonality=False)
            m.fit(train)
            future = m.make_future_dataframe(periods=len(test))
            fc = m.predict(future).tail(len(test))
            # Compare horizon-summed demand.
            yt = test["y"].values[:horizon].sum()
            yp = fc["yhat"].clip(lower=0).values[:horizon].sum()
            if yt > 0:
                wapes.append(abs(yt - yp) / yt)
                mapes.append(abs(yt - yp) / yt)
                rmses.append(abs(yt - yp))
        except Exception:  # noqa: BLE001 - individual series may fail to converge
            continue

    return {
        "wape": float(np.nanmean(wapes)) if wapes else float("nan"),
        "mape": float(np.nanmean(mapes)) if mapes else float("nan"),
        "rmse": float(np.nanmean(rmses)) if rmses else float("nan"),
        "n_series": len(wapes),
        "skipped": False,
    }
