"""Expiry projection, allocation and redistribution logic."""
from __future__ import annotations

from datetime import date, timedelta

from app.services.expiry import (
    assess_batch,
    assess_batches,
    band_for,
    compute_allocation,
    propose_transfers,
)

TODAY = date(2026, 7, 18)


def _batch(lot: str, qty: int, days: int) -> dict:
    return {
        "id": f"b-{lot}",
        "medication_id": "med-1",
        "pharmacy_id": "ph-1",
        "lot_number": lot,
        "quantity": qty,
        "expiry_date": TODAY + timedelta(days=days),
    }


# ── Bands ─────────────────────────────────────────────────────────────────────

def test_lot_expiring_today_counts_as_expired():
    # A lot expiring today cannot be dispensed tomorrow; it must not land in
    # the "less than 30 days" band.
    assert band_for(0)[0] == "Périmé"
    assert band_for(-5)[0] == "Périmé"
    assert band_for(1)[0] == "Moins de 30 jours"


# ── Projection ────────────────────────────────────────────────────────────────

def test_expired_batch_is_a_total_loss():
    r = assess_batch(
        batch_id="b", medication_id="m", pharmacy_id="p", lot_number="L1",
        quantity=500, expiry_date=TODAY - timedelta(days=3),
        daily_rate=10.0, unit_price_tnd=2.0, today=TODAY,
    )
    assert r.projected_consumption == 0
    assert r.at_risk_quantity == 500
    assert r.at_risk_value_tnd == 1000.0


def test_fast_mover_wastes_nothing():
    r = assess_batch(
        batch_id="b", medication_id="m", pharmacy_id="p", lot_number="L1",
        quantity=100, expiry_date=TODAY + timedelta(days=60),
        daily_rate=10.0, unit_price_tnd=1.0, today=TODAY,
    )
    assert r.at_risk_quantity == 0
    assert not r.is_at_risk


def test_slow_mover_wastes_the_surplus():
    # 1/day for 30 days can only clear 30 of the 300 units held.
    r = assess_batch(
        batch_id="b", medication_id="m", pharmacy_id="p", lot_number="L1",
        quantity=300, expiry_date=TODAY + timedelta(days=30),
        daily_rate=1.0, unit_price_tnd=5.0, today=TODAY,
    )
    assert r.projected_consumption == 30
    assert r.at_risk_quantity == 270
    assert r.at_risk_value_tnd == 1350.0


def test_fefo_means_later_lots_inherit_only_leftover_demand():
    """The whole point of FEFO accounting.

    Two lots of 100, rate 10/day. The near lot (10 days) absorbs 100 units of
    demand; the far lot (20 days) has 200 units of capacity but 100 is already
    claimed, so only 100 remains for it. Assessed independently, both would
    look safe and the projection would understate waste.
    """
    risks = assess_batches(
        [_batch("NEAR", 100, 10), _batch("FAR", 100, 20)],
        daily_rate=10.0, unit_price_tnd=1.0, today=TODAY,
    )
    near, far = risks[0], risks[1]
    assert near.lot_number == "NEAR"          # sorted by expiry
    assert near.projected_consumption == 100
    assert far.projected_consumption == 100   # 200 capacity − 100 already claimed
    assert far.at_risk_quantity == 0


def test_fefo_exposes_waste_that_independent_assessment_would_miss():
    # Rate 5/day. Lot A (10 d) can clear 50. Lot B (20 d) has 100 capacity but
    # 50 is consumed by A, leaving 50 for a 200-unit lot → 150 wasted.
    risks = assess_batches(
        [_batch("A", 50, 10), _batch("B", 200, 20)],
        daily_rate=5.0, unit_price_tnd=1.0, today=TODAY,
    )
    assert risks[0].at_risk_quantity == 0
    assert risks[1].at_risk_quantity == 150


# ── Allocation ────────────────────────────────────────────────────────────────

def test_allocation_sizes_to_consumption_not_to_a_threshold():
    risks = assess_batches([_batch("L1", 100, 400)], 2.0, 1.0, TODAY)
    a = compute_allocation(
        medication_id="m", pharmacy_id="p", daily_rate=2.0,
        batch_risks=risks, unit_price_tnd=1.0,
    )
    # 54-day horizon x 2/day = 108 target, minus 100 usable.
    assert a.target_stock == 108
    assert a.recommended_quantity == 8


def test_allocation_ignores_stock_that_will_expire_unsold():
    """Doomed stock must not count as available.

    500 units, 10 days left, 1/day: only 10 will sell. Counting all 500 as
    stock would suppress the order entirely and leave the pharmacy empty once
    the lot is destroyed.
    """
    risks = assess_batches([_batch("L1", 500, 10)], 1.0, 1.0, TODAY)
    a = compute_allocation(
        medication_id="m", pharmacy_id="p", daily_rate=1.0,
        batch_risks=risks, unit_price_tnd=1.0,
    )
    assert a.current_stock == 500
    assert a.usable_stock == 10
    assert a.recommended_quantity == 44      # 54 target − 10 usable
    assert "périmeront" in a.reason


def test_no_consumption_means_no_resupply():
    risks = assess_batches([_batch("L1", 80, 200)], 0.0, 1.0, TODAY)
    a = compute_allocation(
        medication_id="m", pharmacy_id="p", daily_rate=0.0,
        batch_risks=risks, unit_price_tnd=1.0,
    )
    assert a.recommended_quantity == 0
    assert a.surplus_quantity == 80
    assert "transfert" in a.reason


def test_overstocked_pharmacy_gets_a_surplus_not_an_order():
    risks = assess_batches([_batch("L1", 1000, 900)], 2.0, 1.0, TODAY)
    a = compute_allocation(
        medication_id="m", pharmacy_id="p", daily_rate=2.0,
        batch_risks=risks, unit_price_tnd=1.0,
    )
    assert a.recommended_quantity == 0
    assert a.surplus_quantity == 892         # 1000 usable − 108 target
    assert "redistribuer" in a.reason


# ── Redistribution ────────────────────────────────────────────────────────────

def _alloc(pharmacy_id: str, *, at_risk: int = 0, recommend: int = 0, rate: float = 1.0):
    return compute_allocation(
        medication_id="m", pharmacy_id=pharmacy_id, daily_rate=rate,
        batch_risks=[], unit_price_tnd=1.0,
    ).__class__(
        medication_id="m", pharmacy_id=pharmacy_id, daily_rate=rate,
        current_stock=0, usable_stock=0, target_stock=0,
        recommended_quantity=recommend, surplus_quantity=0,
        cover_days_after=0.0, reason="", at_risk_quantity=at_risk,
        at_risk_value_tnd=0.0, unit_price_tnd=1.0,
    )


def test_transfers_skip_lots_that_cannot_survive_the_journey():
    """Stock expiring in 3 days is a write-off, not a transfer.

    Proposing it would book a fictional saving and move the loss to another
    pharmacy's shelf.
    """
    risks = assess_batches([_batch("SOON", 500, 3)], 0.5, 1.0, TODAY)
    transfers = propose_transfers(
        "m",
        donors=[_alloc("ph-1", at_risk=risks[0].at_risk_quantity)],
        receivers=[_alloc("ph-2", recommend=500, rate=10.0)],
        batch_index={"ph-1": risks},
        unit_price_tnd=1.0,
    )
    assert transfers == []


def test_transfer_quantity_is_capped_by_what_the_receiver_can_sell():
    # 60 days left − 7 transport = 53 sellable days at 2/day = 106 units,
    # even though the receiver nominally "wants" 5000.
    risks = assess_batches([_batch("FAR", 5000, 60)], 0.1, 1.0, TODAY)
    transfers = propose_transfers(
        "m",
        donors=[_alloc("ph-1", at_risk=risks[0].at_risk_quantity)],
        receivers=[_alloc("ph-2", recommend=5000, rate=2.0)],
        batch_index={"ph-1": risks},
        unit_price_tnd=1.0,
    )
    assert len(transfers) == 1
    assert transfers[0].quantity == 106
    assert transfers[0].days_to_expiry == 60


def test_transfer_never_returns_stock_to_its_own_holder():
    risks = assess_batches([_batch("FAR", 1000, 90)], 0.1, 1.0, TODAY)
    transfers = propose_transfers(
        "m",
        donors=[_alloc("ph-1", at_risk=risks[0].at_risk_quantity)],
        receivers=[_alloc("ph-1", recommend=900, rate=5.0)],
        batch_index={"ph-1": risks},
        unit_price_tnd=1.0,
    )
    assert transfers == []
