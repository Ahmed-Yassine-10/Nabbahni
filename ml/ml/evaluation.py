"""Forecast evaluation metrics and rolling-origin backtesting."""
from __future__ import annotations

import numpy as np
import pandas as pd


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error — champion selection criterion."""
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else float("nan")


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
    diff = y_true - y_pred
    return float(np.mean(np.maximum(quantile * diff, (quantile - 1) * diff)))


def ci_coverage(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    return float(np.mean((y_true >= lower) & (y_true <= upper)))


def rolling_origin_splits(dates: pd.Series, folds: int, horizon: int):
    """Yield (train_mask, test_mask) tuples over expanding time windows."""
    unique_days = np.sort(dates.unique())
    n = len(unique_days)
    if n < (folds + 1) * horizon:
        # Not enough history — single split at 80%.
        cutoff = unique_days[int(n * 0.8)]
        yield (dates <= cutoff), (dates > cutoff)
        return
    step = (n - horizon) // (folds + 1)
    for i in range(1, folds + 1):
        train_end_idx = step * (i + 1)
        cutoff = unique_days[min(train_end_idx, n - horizon - 1)]
        test_end = unique_days[min(train_end_idx + horizon, n - 1)]
        yield (dates <= cutoff), (dates > cutoff) & (dates <= test_end)
