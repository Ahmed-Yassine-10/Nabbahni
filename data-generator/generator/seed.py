"""Seed the SentinelleRx database with a realistic synthetic Tunisian dataset.

Usage:
    python -m generator.seed --seed 42 [--days 730] [--pharmacies 100] [--reset]

Produces reference data (governorates, medications, suppliers, pharmacies,
users), ~2 years of demand history (sales at medication × governorate grain),
current stock snapshots, national inventory, import orders + shipments with
delays, distribution records, injected shortage episodes (ground truth), and
external signals. Also builds the substitution table via the backend engine.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Reuse the backend's models + engine (single source of truth for the schema).
BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import delete  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    AtcClass,
    DistributionRecord,
    ExternalSignal,
    Governorate,
    ImportOrder,
    Medication,
    NationalStock,
    Pharmacy,
    SalesDaily,
    Shipment,
    ShortageHistory,
    StockBatch,
    StockLevel,
    Substitution,
    Supplier,
    User,
)
from app.services.substitution import MedLite, build_candidates  # noqa: E402

from generator import reference_data as ref  # noqa: E402
from generator.geo import (  # noqa: E402
    jitter_point,
    simple_polygon_geojson,
    voronoi_regions,
)
from generator.simulate import (  # noqa: E402
    MedProfile,
    base_demand,
    build_shortage_episodes,
    in_episode,
)

CHUNK = 20_000


def _bulk(conn, table, rows: list[dict]) -> None:
    for i in range(0, len(rows), CHUNK):
        conn.execute(table.insert(), rows[i : i + CHUNK])


def reset(session) -> None:
    """Delete existing data (child-first) for idempotent re-seeding."""
    for model in (
        Substitution, Shipment, ImportOrder, DistributionRecord, ShortageHistory,
        ExternalSignal, SalesDaily, StockLevel, StockBatch, NationalStock, User, Pharmacy,
        Supplier, Medication, Governorate, AtcClass,
    ):
        session.execute(delete(model))
    session.commit()


def seed(seed_value: int, days: int, n_pharmacies: int, do_reset: bool) -> None:
    rng = random.Random(seed_value)
    session = SessionLocal()
    t0 = time.time()

    if do_reset:
        print("• Resetting existing data…")
        reset(session)

    # ── ATC classes ──
    session.add_all(
        AtcClass(code=c, level=lvl, label_fr=fr, label_ar=ar, parent_code=parent)
        for c, lvl, fr, ar, parent in ref.ATC_CLASSES
    )

    # ── Governorates (with simplified geometry) ──
    # Voronoi tessellation clipped to the national outline gives contiguous
    # regions; the hexagon approximation is the fallback when SciPy is absent.
    cells = voronoi_regions([(lon, lat) for *_, lat, lon in ref.GOVERNORATES])
    governorates: list[Governorate] = []
    for idx, (code, name_fr, name_ar, pop, lat, lon) in enumerate(ref.GOVERNORATES):
        radius = 0.12 + (pop / 1_500_000) * 0.25
        geometry = cells[idx] or simple_polygon_geojson(lat, lon, radius, rng)
        gov = Governorate(
            code=code, name_fr=name_fr, name_ar=name_ar, population=pop,
            centroid_lat=lat, centroid_lon=lon,
            geojson=geometry,
        )
        governorates.append(gov)
        session.add(gov)

    # ── Suppliers ──
    suppliers: list[Supplier] = []
    for name, country, stype, rel, lead in ref.SUPPLIERS:
        sup = Supplier(name=name, country=country, type=stype,
                       reliability_score=rel, avg_lead_time_days=lead)
        suppliers.append(sup)
        session.add(sup)

    # ── Medications ──
    medications: list[Medication] = []
    for (brand, dci, atc, form, dosage, ddd_v, ddd_u, price, essential, rx) in ref.MEDICATIONS:
        med = Medication(
            atc_code=atc, dci=dci, brand_name=brand, form=form, dosage=dosage,
            unit="boîte", ddd_value=ddd_v, ddd_unit=ddd_u, unit_price_tnd=price,
            is_essential=essential, requires_prescription=rx,
        )
        medications.append(med)
        session.add(med)

    session.flush()  # assign PKs
    print(f"• Reference: {len(governorates)} gov, {len(medications)} meds, "
          f"{len(suppliers)} suppliers")

    # ── Pharmacies distributed by population ──
    total_pop = sum(g.population for g in governorates)
    pharmacies: list[Pharmacy] = []
    reference_pharmacy: dict[str, Pharmacy] = {}   # governorate_id -> ref community pharmacy
    demo_elmanar = demo_charles = None

    for gov in governorates:
        share = gov.population / total_pop
        n_comm = max(1, round(n_pharmacies * 0.85 * share))
        n_hosp = max(1, round(n_pharmacies * 0.15 * share))
        for i in range(n_comm):
            lat, lon = jitter_point(float(gov.centroid_lat), float(gov.centroid_lon), 25, rng)
            name = f"Pharmacie {gov.name_fr} {i + 1}"
            if gov.code == "11" and i == 0:
                name = "Pharmacie El Manar"
            ph = Pharmacy(
                name=name, type="community", governorate_id=gov.id,
                address=f"{gov.name_fr}, Tunisie", phone=f"+216 7{rng.randint(1000000, 9999999)}",
                on_call=(i % 7 == 0), latitude=round(lat, 5), longitude=round(lon, 5),
            )
            pharmacies.append(ph)
            session.add(ph)
            if i == 0:
                reference_pharmacy[str(gov.id)] = ph
                if gov.code == "11":
                    demo_elmanar = ph
        for j in range(n_hosp):
            lat, lon = jitter_point(float(gov.centroid_lat), float(gov.centroid_lon), 15, rng)
            name = f"Hôpital {gov.name_fr} {j + 1}"
            if gov.code == "11" and j == 0:
                name = "Hôpital Charles Nicolle"
            ph = Pharmacy(
                name=name, type="hospital", governorate_id=gov.id,
                address=f"{gov.name_fr}, Tunisie", phone=f"+216 7{rng.randint(1000000, 9999999)}",
                on_call=True, latitude=round(lat, 5), longitude=round(lon, 5),
            )
            pharmacies.append(ph)
            session.add(ph)
            if gov.code == "11" and j == 0:
                demo_charles = ph

    session.flush()
    print(f"• Pharmacies: {len(pharmacies)}")

    # ── Demo users (linked to Keycloak subjects = email in dev-token mode) ──
    medis = next(s for s in suppliers if s.name == "MEDIS")
    tunis = next(g for g in governorates if g.code == "11")
    session.add_all([
        User(keycloak_sub="admin@pct.tn", email="admin@pct.tn", full_name="Admin PCT",
             role="pct_admin"),
        User(keycloak_sub="region.tunis@sante.tn", email="region.tunis@sante.tn",
             full_name="Autorité Tunis", role="regional_authority", governorate_id=tunis.id),
        User(keycloak_sub="hopital.charlesnicolle@sante.tn",
             email="hopital.charlesnicolle@sante.tn", full_name="Pharmacien Charles Nicolle",
             role="hospital_pharmacist",
             pharmacy_id=demo_charles.id if demo_charles else None),
        User(keycloak_sub="pharmacie.elmanar@pharma.tn", email="pharmacie.elmanar@pharma.tn",
             full_name="Pharmacien El Manar", role="community_pharmacist",
             pharmacy_id=demo_elmanar.id if demo_elmanar else None),
        User(keycloak_sub="supplier.medis@medis.tn", email="supplier.medis@medis.tn",
             full_name="Fournisseur MEDIS", role="supplier", supplier_id=medis.id),
        User(keycloak_sub="citoyen@demo.tn", email="citoyen@demo.tn", full_name="Citoyen Demo",
             role="citizen"),
    ])
    session.commit()

    # ── Demand profiles per medication ──
    profiles: dict[str, MedProfile] = {}
    for med in medications:
        group = med.atc_code[0]
        if med.dci.startswith("Paracétamol"):
            base = rng.uniform(600, 900)
        elif group == "J":
            base = rng.uniform(90, 180)
        elif group in ("C", "A"):
            base = rng.uniform(120, 260)      # chronic — steady, high
        elif group == "R":
            base = rng.uniform(70, 160)
        else:
            base = rng.uniform(40, 120)
        profiles[str(med.id)] = MedProfile(
            med_id=str(med.id), atc_code=med.atc_code,
            base_daily_per_100k=base,
            trend_per_year=rng.uniform(0.97, 1.09),
            is_essential=med.is_essential,
        )

    start = date.today() - timedelta(days=days)
    gov_ids = [str(g.id) for g in governorates]
    med_ids = [str(m.id) for m in medications]
    episodes = build_shortage_episodes(med_ids, gov_ids, start, days, rng, n_episodes=25)

    # ── Sales history: medication × governorate × day (attributed to ref pharmacy) ──
    print(f"• Simulating {days} days of demand… (this is the heavy step)")
    price_by_med = {str(m.id): float(m.unit_price_tnd) for m in medications}
    pop_by_gov = {str(g.id): g.population for g in governorates}

    sales_rows: list[dict] = []
    with engine.begin() as conn:
        for gi, gov in enumerate(governorates):
            gid = str(gov.id)
            ref_ph = reference_pharmacy[gid]
            for med in medications:
                mid = str(med.id)
                prof = profiles[mid]
                for d in range(days):
                    day = start + timedelta(days=d)
                    demand = base_demand(prof, pop_by_gov[gid], day, d, days, rng)
                    stockout = in_episode(episodes, mid, gid, day)
                    if stockout:
                        # Censored sales during a shortage episode.
                        qty = int(demand * rng.uniform(0.0, 0.25))
                    else:
                        qty = int(round(demand))
                    if qty <= 0 and not stockout:
                        continue
                    sales_rows.append({
                        "pharmacy_id": ref_ph.id,
                        "medication_id": med.id,
                        "date": day,
                        "quantity": qty,
                        "revenue_tnd": round(qty * price_by_med[mid], 3),
                        "stockout": stockout,
                    })
                    if len(sales_rows) >= CHUNK:
                        conn.execute(SalesDaily.__table__.insert(), sales_rows)
                        sales_rows = []
            print(f"    governorate {gi + 1}/{len(governorates)} ({gov.name_fr})", end="\r")
        if sales_rows:
            conn.execute(SalesDaily.__table__.insert(), sales_rows)
    print("\n• Sales history written")

    # ── Current stock snapshots (latest date) for every pharmacy × carried med ──
    # Each pharmacy holds a *share* of its governorate's demand so that the sum
    # across a governorate covers ~`cover` days of that governorate's demand.
    # This keeps coverage_days realistic (episode pairs low, others healthy).
    from collections import Counter

    gov_ph_count = Counter(str(ph.governorate_id) for ph in pharmacies)
    today = date.today()
    stock_rows: list[dict] = []
    batch_specs: list[tuple] = []
    for ph in pharmacies:
        gid = str(ph.governorate_id)
        n_ph = max(1, gov_ph_count[gid])
        for med in medications:
            if rng.random() > 0.7:   # each pharmacy carries ~70% of catalogue
                continue
            mid = str(med.id)
            prof = profiles[mid]
            gov_daily = base_demand(prof, pop_by_gov[gid], today, days, days, rng)
            # This pharmacy's share of governorate demand (~1/N; hospitals hold more).
            share = (2.0 if ph.type == "hospital" else 1.0) / n_ph
            per_ph_daily = gov_daily * share / 0.7   # /0.7 since only ~70% carry
            # Days-of-cover: low during an active episode, healthy otherwise.
            if in_episode(episodes, mid, gid, today):
                cover = rng.uniform(0, 4)
            else:
                cover = rng.uniform(8, 45)
            qty = max(0, int(per_ph_daily * cover))
            stock_rows.append({
                "pharmacy_id": ph.id, "medication_id": med.id,
                "quantity": qty, "min_threshold": max(3, int(per_ph_daily * 7)),
                "recorded_at": today,
            })
            batch_specs.append((ph.id, med.id, qty, cover))
    with engine.begin() as conn:
        _bulk(conn, StockLevel.__table__, stock_rows)
    print(f"• Stock snapshots: {len(stock_rows)}")

    # ── Break each holding into lots with real expiry dates ──
    # Shelf life is 18–36 months from manufacture, but what matters for waste
    # is how much life is LEFT. Over-stocked pharmacies are given shorter-dated
    # lots on purpose: in reality the two travel together — stock sits because
    # it does not sell, and sitting stock is what expires. Without that
    # correlation the expiry analytics would only ever find random noise.
    batch_rows: list[dict] = []
    for ph_id, med_id, qty, cover in batch_specs:
        if qty <= 0:
            continue
        n_lots = 1 if qty < 60 else rng.randint(2, 3)
        remaining = qty
        for i in range(n_lots):
            lot_qty = remaining if i == n_lots - 1 else int(remaining * rng.uniform(0.3, 0.6))
            if lot_qty <= 0:
                continue
            remaining -= lot_qty

            roll = rng.random()
            if cover > 30 and roll < 0.28:
                days_left = rng.randint(-25, 75)      # slow mover, short-dated
            elif roll < 0.06:
                days_left = rng.randint(-40, 20)      # genuine near/at expiry
            elif roll < 0.22:
                days_left = rng.randint(75, 180)
            else:
                days_left = rng.randint(180, 900)

            expiry = today + timedelta(days=days_left)
            shelf_life = rng.choice([540, 730, 1095])
            batch_rows.append({
                "medication_id": med_id,
                "pharmacy_id": ph_id,
                "warehouse": None,
                "lot_number": f"L{rng.randint(100000, 999999)}",
                "quantity": lot_qty,
                "quantity_written_off": 0,
                "manufactured_at": expiry - timedelta(days=shelf_life),
                "expiry_date": expiry,
                "received_at": today - timedelta(days=rng.randint(5, 200)),
            })

    # Central PCT warehouse lots — longer dated, they sit upstream.
    for med in medications:
        for _ in range(rng.randint(1, 3)):
            days_left = rng.randint(120, 1000) if rng.random() > 0.1 else rng.randint(10, 110)
            expiry = today + timedelta(days=days_left)
            batch_rows.append({
                "medication_id": med.id,
                "pharmacy_id": None,
                "warehouse": "PCT Tunis",
                "lot_number": f"C{rng.randint(100000, 999999)}",
                "quantity": rng.randint(5_000, 120_000),
                "quantity_written_off": 0,
                "manufactured_at": expiry - timedelta(days=730),
                "expiry_date": expiry,
                "received_at": today - timedelta(days=rng.randint(10, 300)),
            })

    with engine.begin() as conn:
        _bulk(conn, StockBatch.__table__, batch_rows)
    expired_now = sum(1 for b in batch_rows if b["expiry_date"] <= today)
    print(f"• Stock batches: {len(batch_rows)}  ({expired_now} already expired)")

    # ── National inventory: daily per medication (drops during national episodes) ──
    nat_rows: list[dict] = []
    for med in medications:
        mid = str(med.id)
        prof = profiles[mid]
        national_daily = prof.base_daily_per_100k * (total_pop / 100_000)
        normal_level = national_daily * rng.uniform(45, 75)
        for d in range(0, days, 7):   # weekly snapshots keep the table lean
            day = start + timedelta(days=d)
            factor = 1.0
            if in_episode(episodes, mid, None, day):
                factor = rng.uniform(0.05, 0.25)
            qty = max(0, int(normal_level * factor * rng.uniform(0.85, 1.15)))
            nat_rows.append({
                "medication_id": med.id, "quantity": qty, "warehouse": "PCT Tunis",
                "recorded_at": day,
            })
        # Ensure a current row.
        cur_factor = 0.15 if in_episode(episodes, mid, None, today) else rng.uniform(0.4, 1.1)
        nat_rows.append({
            "medication_id": med.id, "quantity": max(0, int(normal_level * cur_factor)),
            "warehouse": "PCT Tunis", "recorded_at": today,
        })
    with engine.begin() as conn:
        _bulk(conn, NationalStock.__table__, nat_rows)
    print(f"• National stock rows: {len(nat_rows)}")

    # ── Import orders + shipments (supplier delay signal) ──
    import_rows: list[dict] = []
    for med in medications:
        supplier = rng.choice(suppliers)
        # Monthly-ish import cycle.
        for d in range(0, days, rng.randint(25, 40)):
            ordered = start + timedelta(days=d)
            promised = ordered + timedelta(days=supplier.avg_lead_time_days)
            # Reliability drives delay distribution.
            delay = max(0, int(rng.gauss((1 - float(supplier.reliability_score)) * 30, 6)))
            arrived = promised + timedelta(days=delay)
            import_rows.append({
                "supplier_id": supplier.id, "medication_id": med.id,
                "quantity": rng.randint(500, 5000),
                "ordered_at": ordered, "promised_at": promised,
                "arrived_at": arrived if arrived <= today else None,
                "port": "Radès", "status": "arrived" if arrived <= today else "in_transit",
            })
    with engine.begin() as conn:
        result = conn.execute(
            ImportOrder.__table__.insert().returning(ImportOrder.id, ImportOrder.promised_at),
            import_rows,
        )
        import_ids = result.fetchall()
    # One shipment per import order.
    ship_rows = []
    for (io_id, promised), row in zip(import_ids, import_rows, strict=False):
        ship_rows.append({
            "import_order_id": io_id,
            "promised_date": row["promised_at"],
            "actual_date": row["arrived_at"],
            "status": "arrived" if row["arrived_at"] else "in_transit",
        })
    with engine.begin() as conn:
        _bulk(conn, Shipment.__table__, ship_rows)
    print(f"• Import orders + shipments: {len(import_rows)}")

    # ── Distribution records (national warehouse → governorates) ──
    dist_rows = []
    for med in medications:
        for gov in governorates:
            for d in range(0, days, rng.randint(20, 35)):
                shipped = start + timedelta(days=d)
                lag = rng.randint(1, 6)
                dist_rows.append({
                    "medication_id": med.id, "governorate_id": gov.id,
                    "quantity": rng.randint(50, 800),
                    "shipped_at": shipped, "received_at": shipped + timedelta(days=lag),
                })
    with engine.begin() as conn:
        _bulk(conn, DistributionRecord.__table__, dist_rows)
    print(f"• Distribution records: {len(dist_rows)}")

    # ── Shortage history (ground truth for the classifier) ──
    hist_rows = [{
        "medication_id": ep.med_id, "governorate_id": ep.governorate_id,
        "started_at": ep.start, "ended_at": ep.end if ep.end <= today else None,
        "severity": "critical" if (ep.end - ep.start).days > 30 else "red",
        "cause": ep.cause,
    } for ep in episodes]
    with engine.begin() as conn:
        _bulk(conn, ShortageHistory.__table__, hist_rows)
    print(f"• Shortage episodes: {len(hist_rows)}")

    # ── External signals ──
    signal_rows = []
    for gov in governorates:
        for d in range(0, days, 7):
            day = start + timedelta(days=d)
            month = day.month
            temp = 12 + 14 * (1 + (month - 1) / 12) + rng.gauss(0, 3)
            signal_rows.append({
                "signal_type": "weather", "region": gov.name_fr, "date": day,
                "payload": {"temp_c": round(temp, 1), "humidity": rng.randint(30, 90)},
                "source": "INM (synthétique)",
            })
    # National flu index (weekly).
    for d in range(0, days, 7):
        day = start + timedelta(days=d)
        doy = day.timetuple().tm_yday
        flu = max(0, 50 + 45 * math.cos(2 * math.pi * (doy - 15) / 365))
        signal_rows.append({
            "signal_type": "epidemiological", "region": None, "date": day,
            "payload": {"flu_index": round(flu, 1)}, "source": "ONMNE (synthétique)",
        })
    # A few WHO / ministry alerts.
    for i in range(6):
        day = start + timedelta(days=rng.randint(0, days - 1))
        signal_rows.append({
            "signal_type": rng.choice(["who_alert", "ministry"]),
            "region": None, "date": day,
            "payload": {"headline": "Alerte d'approvisionnement mondiale sur certains antibiotiques"},
            "source": "WHO" if i % 2 else "Ministère de la Santé",
            "note": "Événement synthétique de démonstration",
        })
    with engine.begin() as conn:
        _bulk(conn, ExternalSignal.__table__, signal_rows)
    print(f"• External signals: {len(signal_rows)}")

    # ── Substitutions via the backend engine ──
    med_lites = [
        MedLite(id=str(m.id), atc_code=m.atc_code, dci=m.dci,
                ddd_value=float(m.ddd_value) if m.ddd_value else None)
        for m in medications
    ]
    candidates = build_candidates(med_lites)
    sub_rows = [{
        "source_medication_id": c.source_id, "target_medication_id": c.target_id,
        "atc_match_level": c.atc_match_level,
        "equivalence": c.equivalence.value,
        "ddd_ratio": c.ddd_ratio, "notes_fr": c.notes_fr,
        "requires_pharmacist_validation": True,
    } for c in candidates]
    with engine.begin() as conn:
        _bulk(conn, Substitution.__table__, sub_rows)
    print(f"• Substitutions: {len(sub_rows)}")

    session.close()
    print(f"\n✅ Seed complete in {time.time() - t0:.1f}s")


def main() -> None:
    p = argparse.ArgumentParser(description="Seed SentinelleRx synthetic data")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--days", type=int, default=730)
    p.add_argument("--pharmacies", type=int, default=100)
    p.add_argument("--reset", action="store_true", default=True)
    p.add_argument("--no-reset", dest="reset", action="store_false")
    args = p.parse_args()
    seed(args.seed, args.days, args.pharmacies, args.reset)


if __name__ == "__main__":
    main()
