"""Administrative endpoints: scoring trigger, model runs, audit log."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.security import Principal, require_roles
from app.models.ml import ModelRun
from app.models.ops import AuditLog

router = APIRouter()


@router.post("/admin/scoring/run", summary="Trigger a batch scoring run (async)")
def run_scoring(
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_roles(Role.pct_admin)),
) -> dict[str, str]:
    # The heavy scoring job lives in the ml package; here we kick it off out-of-band.
    # In production this enqueues a job; locally it runs the module in the background.
    def _run() -> None:
        import subprocess
        import sys

        subprocess.run([sys.executable, "-m", "ml.score"], check=False)

    background_tasks.add_task(_run)
    return {"status": "scoring_started"}


@router.get("/admin/model-runs", summary="Registered model runs and metrics")
def model_runs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.pct_admin)),
) -> list[dict]:
    rows = db.scalars(
        select(ModelRun).order_by(ModelRun.trained_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "model_family": r.model_family,
            "model_type": r.model_type,
            "horizon_days": r.horizon_days,
            "metrics": r.metrics,
            "is_champion": r.is_champion,
            "mlflow_run_id": r.mlflow_run_id,
            "trained_at": r.trained_at.isoformat() if r.trained_at else None,
        }
        for r in rows
    ]


@router.get("/admin/audit-logs", summary="Audit trail (append-only)")
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.pct_admin)),
) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.at.desc()).limit(limit)).all()
    return [
        {
            "id": str(r.id),
            "user_sub": r.user_sub,
            "role": r.role,
            "action": r.action,
            "resource": r.resource,
            "status_code": r.status_code,
            "ip": r.ip,
            "at": r.at.isoformat() if r.at else None,
        }
        for r in rows
    ]
