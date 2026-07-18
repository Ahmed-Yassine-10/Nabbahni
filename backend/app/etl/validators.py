"""Validation + normalization for inbound data-hub records.

Each connector (pharmacy POS, PCT ERP, supplier EDI, external signals) feeds raw
records through a validator before they reach the transactional tables. Invalid
rows are quarantined with a reason rather than silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ValidationResult:
    valid: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[tuple[dict[str, Any], str]] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {"valid": len(self.valid), "rejected": len(self.rejected)}


def _is_iso_date(value: Any) -> bool:
    if isinstance(value, date):
        return True
    try:
        date.fromisoformat(str(value))
        return True
    except (ValueError, TypeError):
        return False


def validate_stock_records(records: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    for rec in records:
        if "medication_id" not in rec:
            result.rejected.append((rec, "medication_id manquant"))
            continue
        qty = rec.get("quantity")
        if not isinstance(qty, int) or qty < 0:
            result.rejected.append((rec, "quantité invalide"))
            continue
        if rec.get("recorded_at") and not _is_iso_date(rec["recorded_at"]):
            result.rejected.append((rec, "date invalide"))
            continue
        result.valid.append(rec)
    return result


def validate_sales_records(records: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    for rec in records:
        if not {"pharmacy_id", "medication_id", "date"} <= rec.keys():
            result.rejected.append((rec, "champs obligatoires manquants"))
            continue
        if not _is_iso_date(rec["date"]):
            result.rejected.append((rec, "date invalide"))
            continue
        if rec.get("quantity", 0) < 0:
            result.rejected.append((rec, "quantité négative"))
            continue
        result.valid.append(rec)
    return result


def validate_external_signal(record: dict[str, Any]) -> tuple[bool, str | None]:
    valid_types = {
        "weather", "epidemiological", "who_alert", "ministry", "economic", "logistics",
    }
    if record.get("signal_type") not in valid_types:
        return False, "type de signal inconnu"
    if not _is_iso_date(record.get("date")):
        return False, "date invalide"
    if not isinstance(record.get("payload", {}), dict):
        return False, "payload doit être un objet"
    return True, None
