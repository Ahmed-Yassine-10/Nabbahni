"""End-to-end training: demand models (XGB/LGBM/Prophet) + shortage classifier.

Run with:  python -m ml.train_all
Logs runs to MLflow when reachable, always persists champions locally for
scoring, writes model_runs rows to the database, and emits a comparison report
at ml/reports/model_comparison.md.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import SessionLocal
from app.models import ModelRun
from ml import data as dataio
from ml.config import HORIZONS, TrainConfig
from ml.features import build_series_features
from ml.registry import mlflow_available, save_local
from ml.shortage import build_training_table, train_classifier
from ml.training.demand import train_boosted, train_prophet_national

logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ml.train_all")

REPORT = Path(__file__).resolve().parents[1] / "reports" / "model_comparison.md"


def _record_run(session, family, model_type, horizon, metrics, champion, mlflow_run_id=None):
    session.add(ModelRun(
        mlflow_run_id=mlflow_run_id, model_family=family, model_type=model_type,
        horizon_days=horizon, metrics=metrics, is_champion=champion,
        trained_at=datetime.now(timezone.utc),
    ))


def main() -> None:
    cfg = TrainConfig()
    log.info("Loading data…")
    sales = dataio.load_sales_by_gov()
    meds = dataio.load_medications()
    flu = dataio.load_flu_index()
    if sales.empty:
        raise SystemExit("No sales data found. Run `make seed` first.")

    log.info("Engineering features (%d sales rows)…", len(sales))
    features = build_series_features(sales, meds, flu, cfg.horizons)

    use_mlflow = mlflow_available()
    if use_mlflow:
        import mlflow

        mlflow.set_experiment("sentinellerx-demand")

    session = SessionLocal()
    comparison_rows: list[dict] = []

    for h in cfg.horizons:
        log.info("── Horizon %d days ──", h)
        results = {}
        for family in ("xgboost", "lightgbm"):
            model = train_boosted(family, features, h, cfg.quantiles, cfg.backtest_folds)
            results[family] = model
            save_local(model, f"demand-{family}-{h}")
            if use_mlflow:
                import mlflow

                with mlflow.start_run(run_name=f"{family}-{h}d"):
                    mlflow.log_params({"family": family, "horizon": h})
                    mlflow.log_metrics({k: v for k, v in model.metrics.items()
                                        if isinstance(v, (int, float))})

        prophet_metrics = train_prophet_national(sales, meds, h, cfg.prophet_top_series)
        comparison_rows.append({"horizon": h, "family": "prophet", **prophet_metrics})

        # Champion = lowest WAPE among boosted models (Prophet benchmarked separately).
        champion_family = min(results, key=lambda f: _safe(results[f].metrics.get("wape")))
        for family, model in results.items():
            is_champ = family == champion_family
            _record_run(session, family, "demand", h, model.metrics, is_champ)
            comparison_rows.append({"horizon": h, "family": family, **model.metrics})
            if is_champ:
                save_local(model, f"demand-champion-{h}")
                log.info("Champion h=%d → %s (WAPE=%.3f)", h, family,
                         _safe(model.metrics.get("wape")))
        _record_run(session, "prophet", "demand", h, prophet_metrics, False)

    # ── Shortage classifier ──
    log.info("Training shortage classifier…")
    nat_hist = dataio.load_national_stock_history()
    delays = dataio.load_supplier_delays()
    table = build_training_table(sales, meds, nat_hist, delays, flu, horizon=30)
    if table.empty:
        log.warning("No shortage training rows produced")
    else:
        smodel = train_classifier(table)
        save_local(smodel, "shortage")
        _record_run(session, "lightgbm", "shortage", 30, smodel.metrics, True)
        if use_mlflow:
            import mlflow

            mlflow.set_experiment("sentinellerx-shortage")
            with mlflow.start_run(run_name="shortage-clf"):
                mlflow.log_metrics({k: v for k, v in smodel.metrics.items()
                                    if isinstance(v, (int, float))})

    session.commit()
    session.close()

    _write_report(comparison_rows)
    log.info("✅ Training complete. Report: %s", REPORT)


def _safe(v) -> float:
    try:
        f = float(v)
        return f if f == f else 1e9  # NaN → large
    except (TypeError, ValueError):
        return 1e9


def _write_report(rows: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    by_h: dict[int, list[dict]] = {}
    for r in rows:
        by_h.setdefault(r["horizon"], []).append(r)

    lines = [
        "# SentinelleRx — Demand Model Comparison",
        "",
        "Champion per horizon selected by lowest **WAPE** (Weighted Absolute "
        "Percentage Error). Prophet is benchmarked on the top national series only.",
        "",
    ]
    horizon_label = {7: "1 semaine", 14: "2 semaines", 30: "1 mois", 90: "3 mois"}
    for h in sorted(by_h):
        lines.append(f"## Horizon {h} jours ({horizon_label.get(h, '')})")
        lines.append("")
        lines.append("| Modèle | WAPE | MAPE | RMSE | n |")
        lines.append("|---|---|---|---|---|")
        best = min((x for x in by_h[h] if x["family"] != "prophet"),
                   key=lambda x: _safe(x.get("wape")), default=None)
        for r in by_h[h]:
            star = " ⭐" if best and r["family"] == best["family"] else ""
            n = r.get("n_train") or r.get("n_series") or "—"
            lines.append(
                f"| {r['family']}{star} | {_fmt(r.get('wape'))} | {_fmt(r.get('mape'))} "
                f"| {_fmt(r.get('rmse'))} | {n} |"
            )
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def _fmt(v) -> str:
    try:
        f = float(v)
        return f"{f:.3f}" if f == f else "n/a"
    except (TypeError, ValueError):
        return "n/a"


if __name__ == "__main__":
    main()
