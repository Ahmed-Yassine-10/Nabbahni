"""MLflow tracking + model registry helpers with a local-file fallback."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import joblib

from app.core.config import settings

log = logging.getLogger("ml.registry")

_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
_ARTIFACT_DIR.mkdir(exist_ok=True)


def mlflow_available() -> bool:
    try:
        import mlflow  # noqa: F401

        os.environ.setdefault("MLFLOW_TRACKING_URI", settings.mlflow_tracking_uri)
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        # Probe the tracking server; fall back to local files if unreachable.
        mlflow.search_experiments(max_results=1)
        return True
    except Exception as exc:  # pragma: no cover
        log.warning("MLflow unavailable (%s); using local artifact store", exc)
        return False


def save_local(model, name: str) -> Path:
    path = _ARTIFACT_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    return path


def load_local(name: str):
    path = _ARTIFACT_DIR / f"{name}.joblib"
    return joblib.load(path) if path.exists() else None
