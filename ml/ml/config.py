"""ML pipeline configuration."""
from __future__ import annotations

from dataclasses import dataclass, field

# Forecast horizons in days — 1 week, 2 weeks, 1 month, 3 months.
HORIZONS = [7, 14, 30, 90]

# Registered model name templates.
DEMAND_MODEL_NAME = "sentinellerx-demand-{h}d"
SHORTAGE_MODEL_NAME = "sentinellerx-shortage"

EXPERIMENT_DEMAND = "sentinellerx-demand"
EXPERIMENT_SHORTAGE = "sentinellerx-shortage"


@dataclass
class TrainConfig:
    horizons: list[int] = field(default_factory=lambda: list(HORIZONS))
    quantiles: tuple[float, float, float] = (0.1, 0.5, 0.9)
    backtest_folds: int = 3
    prophet_top_series: int = 40      # Prophet only on the busiest national series
    random_state: int = 42
    min_history_days: int = 120
