"""Data access for ML — loads DB tables into pandas frames."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    ExternalSignal,
    Governorate,
    ImportOrder,
    Medication,
    NationalStock,
    Pharmacy,
    SalesDaily,
    ShortageHistory,
    StockLevel,
)


def load_sales_by_gov() -> pd.DataFrame:
    """Daily sales aggregated to medication × governorate."""
    with SessionLocal() as s:
        rows = s.execute(
            select(
                SalesDaily.medication_id,
                Pharmacy.governorate_id,
                SalesDaily.date,
                SalesDaily.quantity,
                SalesDaily.stockout,
            ).join(Pharmacy, SalesDaily.pharmacy_id == Pharmacy.id)
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "governorate_id", "date", "quantity",
                                     "stockout"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["medication_id"] = df["medication_id"].astype(str)
    df["governorate_id"] = df["governorate_id"].astype(str)
    grouped = (
        df.groupby(["medication_id", "governorate_id", "date"], as_index=False)
        .agg(quantity=("quantity", "sum"), stockout=("stockout", "max"))
    )
    return grouped


def load_medications() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.execute(
            select(
                Medication.id, Medication.atc_code, Medication.dci, Medication.brand_name,
                Medication.unit_price_tnd, Medication.is_essential, Medication.ddd_value,
            )
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "atc_code", "dci", "brand_name",
                                     "unit_price_tnd", "is_essential", "ddd_value"])
    df["medication_id"] = df["medication_id"].astype(str)
    return df


def load_governorates() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.execute(
            select(Governorate.id, Governorate.code, Governorate.name_fr, Governorate.population)
        ).all()
    df = pd.DataFrame(rows, columns=["governorate_id", "code", "name_fr", "population"])
    df["governorate_id"] = df["governorate_id"].astype(str)
    return df


def load_current_stock() -> pd.DataFrame:
    """Latest stock quantity summed to medication × governorate."""
    with SessionLocal() as s:
        rows = s.execute(
            select(
                StockLevel.medication_id, Pharmacy.governorate_id,
                StockLevel.quantity, StockLevel.recorded_at,
            ).join(Pharmacy, StockLevel.pharmacy_id == Pharmacy.id)
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "governorate_id", "quantity", "recorded_at"])
    if df.empty:
        return df
    df["medication_id"] = df["medication_id"].astype(str)
    df["governorate_id"] = df["governorate_id"].astype(str)
    latest = df.groupby(["medication_id", "governorate_id"], as_index=False).agg(
        stock_qty=("quantity", "sum")
    )
    return latest


def load_national_stock_latest() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.execute(
            select(NationalStock.medication_id, NationalStock.quantity, NationalStock.recorded_at)
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "quantity", "recorded_at"])
    if df.empty:
        return df
    df["medication_id"] = df["medication_id"].astype(str)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    idx = df.groupby("medication_id")["recorded_at"].idxmax()
    latest = df.loc[idx, ["medication_id", "quantity"]].rename(
        columns={"quantity": "national_stock"}
    )
    return latest.reset_index(drop=True)


def load_national_stock_history() -> pd.DataFrame:
    """Full national inventory history (for coverage features during training)."""
    with SessionLocal() as s:
        rows = s.execute(
            select(NationalStock.medication_id, NationalStock.quantity, NationalStock.recorded_at)
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "quantity", "recorded_at"])
    if df.empty:
        return df
    df["medication_id"] = df["medication_id"].astype(str)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df.sort_values(["medication_id", "recorded_at"])


def load_supplier_delays() -> pd.DataFrame:
    """Recent supplier delay statistics per medication (from import orders)."""
    with SessionLocal() as s:
        rows = s.execute(
            select(
                ImportOrder.medication_id, ImportOrder.promised_at, ImportOrder.arrived_at,
            )
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "promised_at", "arrived_at"])
    if df.empty:
        return df
    df["medication_id"] = df["medication_id"].astype(str)
    df = df.dropna(subset=["arrived_at"])
    df["delay_days"] = (pd.to_datetime(df["arrived_at"]) - pd.to_datetime(df["promised_at"])).dt.days
    stats = df.groupby("medication_id", as_index=False).agg(
        supplier_delay_mean=("delay_days", "mean"),
        supplier_delay_max=("delay_days", "max"),
        supplier_delay_std=("delay_days", "std"),
    )
    return stats.fillna(0)


def load_shortage_history() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.execute(
            select(
                ShortageHistory.medication_id, ShortageHistory.governorate_id,
                ShortageHistory.started_at, ShortageHistory.ended_at,
            )
        ).all()
    df = pd.DataFrame(rows, columns=["medication_id", "governorate_id", "started_at", "ended_at"])
    if df.empty:
        return df
    df["medication_id"] = df["medication_id"].astype(str)
    df["governorate_id"] = df["governorate_id"].astype("string")
    return df


def load_flu_index() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.execute(
            select(ExternalSignal.date, ExternalSignal.payload).where(
                ExternalSignal.signal_type == "epidemiological"
            )
        ).all()
    if not rows:
        return pd.DataFrame(columns=["date", "flu_index"])
    df = pd.DataFrame(
        [{"date": r[0], "flu_index": (r[1] or {}).get("flu_index", 0)} for r in rows]
    )
    df["date"] = pd.to_datetime(df["date"])
    return df
