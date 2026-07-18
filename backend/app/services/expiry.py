"""Expiry risk, waste projection and per-pharmacy allocation.

Two questions this module answers:

  1. *How much stock will expire before it can be sold?*  For each lot we
     compare the quantity on hand against how much that pharmacy will actually
     consume before the lot's expiry date. The surplus is projected waste, in
     units and in dinars.

  2. *How much should each pharmacy receive?*  Ordering to a fixed threshold
     is what creates the waste in the first place: a pharmacy that sells 3
     boxes a month does not need 200. The allocation below sizes each delivery
     to observed consumption plus a safety margin, and refuses to top up stock
     that is already doomed to expire.

Consumption rates come from `demand.pharmacy_daily_rates`, which apportions
governorate-level sales by each pharmacy's share of regional stock — sales are
not recorded per counter (see that module for why).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

# Expiry bands used across the API and the UI. Ordered soonest-first.
# Upper bound is exclusive. A lot expiring TODAY (days_to_expiry == 0) counts
# as expired — it cannot be dispensed tomorrow — so the first band runs to 1,
# matching the `days <= 0` test used for the projection.
EXPIRY_BANDS: list[tuple[str, int | None, int | None, str]] = [
    ("Périmé", None, 1, "critical"),
    ("Moins de 30 jours", 1, 30, "red"),
    ("30 à 90 jours", 30, 90, "orange"),
    ("90 à 180 jours", 90, 180, "yellow"),
    ("Plus de 180 jours", 180, None, "green"),
]

# A lot is flagged "at risk" when this share of it cannot be consumed in time.
_AT_RISK_SHARE = 0.05


@dataclass
class BatchRisk:
    batch_id: str
    medication_id: str
    pharmacy_id: str | None
    lot_number: str
    quantity: int
    expiry_date: date
    days_to_expiry: int
    daily_rate: float
    projected_consumption: int
    at_risk_quantity: int
    at_risk_value_tnd: float
    severity: str

    @property
    def is_at_risk(self) -> bool:
        return self.quantity > 0 and self.at_risk_quantity / self.quantity >= _AT_RISK_SHARE


def band_for(days_to_expiry: int) -> tuple[str, str]:
    """Return (label, severity) for a time-to-expiry in days."""
    for label, lo, hi, severity in EXPIRY_BANDS:
        lo_ok = lo is None or days_to_expiry >= lo
        hi_ok = hi is None or days_to_expiry < hi
        if lo_ok and hi_ok:
            return label, severity
    return EXPIRY_BANDS[-1][0], EXPIRY_BANDS[-1][3]


def assess_batch(
    *,
    batch_id: str,
    medication_id: str,
    pharmacy_id: str | None,
    lot_number: str,
    quantity: int,
    expiry_date: date,
    daily_rate: float,
    unit_price_tnd: float,
    today: date | None = None,
    prior_demand_units: float = 0.0,
) -> BatchRisk:
    """Project how much of one lot will expire unsold.

    `prior_demand_units` is the demand already claimed by lots that expire
    earlier. Stock rotates FEFO (first-expired, first-out), so a lot only gets
    the consumption left over once shorter-dated lots have been sold — without
    this, every lot would optimistically assume the full sales rate and the
    projection would understate waste badly.
    """
    today = today or date.today()
    days = (expiry_date - today).days

    if days <= 0:
        # Already expired: the whole remaining quantity is a loss.
        at_risk = quantity
        projected = 0
    else:
        capacity = daily_rate * days
        projected = int(max(0.0, min(float(quantity), capacity - prior_demand_units)))
        at_risk = max(0, quantity - projected)

    label, severity = band_for(days)
    return BatchRisk(
        batch_id=batch_id,
        medication_id=medication_id,
        pharmacy_id=pharmacy_id,
        lot_number=lot_number,
        quantity=quantity,
        expiry_date=expiry_date,
        days_to_expiry=days,
        daily_rate=round(daily_rate, 3),
        projected_consumption=projected,
        at_risk_quantity=at_risk,
        at_risk_value_tnd=round(at_risk * unit_price_tnd, 2),
        severity=severity,
    )


def assess_batches(
    batches: list[dict],
    daily_rate: float,
    unit_price_tnd: float,
    today: date | None = None,
) -> list[BatchRisk]:
    """Assess every lot of one (pharmacy, medication) pair under FEFO rotation."""
    today = today or date.today()
    ordered = sorted(batches, key=lambda b: b["expiry_date"])
    results: list[BatchRisk] = []
    claimed = 0.0
    for b in ordered:
        risk = assess_batch(
            batch_id=str(b["id"]),
            medication_id=str(b["medication_id"]),
            pharmacy_id=str(b["pharmacy_id"]) if b.get("pharmacy_id") else None,
            lot_number=b["lot_number"],
            quantity=b["quantity"],
            expiry_date=b["expiry_date"],
            daily_rate=daily_rate,
            unit_price_tnd=unit_price_tnd,
            today=today,
            prior_demand_units=claimed,
        )
        results.append(risk)
        claimed += risk.projected_consumption
    return results


# ── Allocation ────────────────────────────────────────────────────────────────

@dataclass
class Allocation:
    """How much of one medication a pharmacy should actually receive."""

    medication_id: str
    pharmacy_id: str
    daily_rate: float
    current_stock: int
    usable_stock: int              # excludes what will expire before it can sell
    target_stock: int
    recommended_quantity: int
    surplus_quantity: int          # > 0 means it already holds too much
    cover_days_after: float
    reason: str
    at_risk_quantity: int = 0
    at_risk_value_tnd: float = 0.0
    unit_price_tnd: float = 0.0

    @property
    def order_value_tnd(self) -> float:
        return round(self.recommended_quantity * self.unit_price_tnd, 2)


def compute_allocation(
    *,
    medication_id: str,
    pharmacy_id: str,
    daily_rate: float,
    batch_risks: list[BatchRisk],
    unit_price_tnd: float,
    lead_time_days: int = 14,
    safety_days: int = 10,
    review_days: int = 30,
) -> Allocation:
    """Size the next delivery to what the pharmacy can actually sell.

    target = consumption over (review period + lead time + safety margin)

    The order is placed against *usable* stock — units projected to sell before
    their lot expires — not against the raw shelf count. Counting doomed stock
    as available is precisely how a pharmacy ends up both over-supplied and
    out of stock at once.
    """
    current = sum(b.quantity for b in batch_risks)
    at_risk = sum(b.at_risk_quantity for b in batch_risks)
    at_risk_value = round(sum(b.at_risk_value_tnd for b in batch_risks), 2)
    usable = max(0, current - at_risk)

    horizon = review_days + lead_time_days + safety_days
    target = int(math.ceil(daily_rate * horizon))

    if daily_rate <= 0:
        # No observed consumption: never push more stock in. If any is held,
        # it is a redistribution candidate, not a re-order.
        return Allocation(
            medication_id=medication_id,
            pharmacy_id=pharmacy_id,
            daily_rate=0.0,
            current_stock=current,
            usable_stock=usable,
            target_stock=0,
            recommended_quantity=0,
            surplus_quantity=current,
            cover_days_after=float("inf") if current else 0.0,
            reason="Aucune consommation observée — ne pas réapprovisionner ; "
                   "envisager un transfert vers une pharmacie qui l'utilise.",
            at_risk_quantity=at_risk,
            at_risk_value_tnd=at_risk_value,
            unit_price_tnd=unit_price_tnd,
        )

    recommended = max(0, target - usable)
    surplus = max(0, usable - target)
    cover_after = round((usable + recommended) / daily_rate, 1)

    if surplus > 0:
        reason = (
            f"Stock utilisable ({usable}) supérieur au besoin de {horizon} jours "
            f"({target}). Excédent de {surplus} unités à redistribuer plutôt "
            f"qu'à recommander."
        )
    elif at_risk > 0:
        reason = (
            f"{at_risk} unités périmeront avant d'être vendues. Commande calculée "
            f"sur le stock réellement écoulable ({usable}), pas sur le stock "
            f"affiché ({current})."
        )
    else:
        reason = (
            f"Couverture cible de {horizon} jours "
            f"(réappro {review_days} j + délai {lead_time_days} j + sécurité {safety_days} j)."
        )

    return Allocation(
        medication_id=medication_id,
        pharmacy_id=pharmacy_id,
        daily_rate=round(daily_rate, 3),
        current_stock=current,
        usable_stock=usable,
        target_stock=target,
        recommended_quantity=recommended,
        surplus_quantity=surplus,
        cover_days_after=cover_after,
        reason=reason,
        at_risk_quantity=at_risk,
        at_risk_value_tnd=at_risk_value,
        unit_price_tnd=unit_price_tnd,
    )


# ── Redistribution ────────────────────────────────────────────────────────────

@dataclass
class Transfer:
    """A proposed movement of soon-to-expire stock between pharmacies."""

    medication_id: str
    from_pharmacy_id: str
    to_pharmacy_id: str
    quantity: int
    expiry_date: date
    days_to_expiry: int
    value_saved_tnd: float
    rationale: str


def propose_transfers(
    medication_id: str,
    donors: list[Allocation],
    receivers: list[Allocation],
    batch_index: dict[str, list[BatchRisk]],
    unit_price_tnd: float,
    max_transfers: int = 50,
    transfer_lead_days: int = 7,
    min_sellable_days: int = 14,
) -> list[Transfer]:
    """Match pharmacies holding doomed stock to pharmacies that will sell it.

    Two constraints make the difference between a real saving and a fictional
    one:

      * **The lot must survive the journey.** A lot expiring tomorrow cannot be
        picked, shipped and dispensed. Anything with less life than
        `transfer_lead_days + min_sellable_days` is written off where it
        stands — moving it only relocates the loss.
      * **The receiver must actually consume it.** The quantity is capped by
        what the destination can sell in the window that remains after
        transport, not by what it nominally "needs". Shipping 10 000 boxes to a
        pharmacy that sells 20 a day just moves the expiry to a new address.

    Purely a proposal — a pharmacist validates every move.
    """
    min_life = transfer_lead_days + min_sellable_days

    supply: list[tuple[BatchRisk, str]] = []
    for donor in donors:
        if donor.at_risk_quantity <= 0:
            continue
        for risk in batch_index.get(donor.pharmacy_id, []):
            if risk.at_risk_quantity > 0 and risk.days_to_expiry >= min_life:
                supply.append((risk, donor.pharmacy_id))

    # Soonest-expiring *salvageable* stock first — it is the most urgent to
    # move, but everything here has enough life to be worth moving.
    supply.sort(key=lambda pair: pair[0].days_to_expiry)

    # Track both the unmet need and the daily rate, so capacity can be capped.
    need: list[list] = [
        [r.pharmacy_id, r.recommended_quantity, r.daily_rate]
        for r in sorted(receivers, key=lambda r: -r.recommended_quantity)
        if r.recommended_quantity > 0 and r.daily_rate > 0
    ]

    transfers: list[Transfer] = []
    for risk, donor_id in supply:
        remaining = risk.at_risk_quantity
        sellable_days = risk.days_to_expiry - transfer_lead_days
        for entry in need:
            if remaining <= 0 or len(transfers) >= max_transfers:
                break
            receiver_id, wanted, rate = entry
            if wanted <= 0 or receiver_id == donor_id:
                continue
            # What this receiver can genuinely sell before the lot expires.
            capacity = int(rate * sellable_days)
            qty = min(remaining, wanted, capacity)
            if qty <= 0:
                continue
            transfers.append(
                Transfer(
                    medication_id=medication_id,
                    from_pharmacy_id=donor_id,
                    to_pharmacy_id=receiver_id,
                    quantity=qty,
                    expiry_date=risk.expiry_date,
                    days_to_expiry=risk.days_to_expiry,
                    value_saved_tnd=round(qty * unit_price_tnd, 2),
                    rationale=(
                        f"Lot {risk.lot_number} expire dans {risk.days_to_expiry} jours et ne "
                        f"sera pas écoulé sur place. Après {transfer_lead_days} j de transport, "
                        f"la pharmacie destinataire peut en vendre {capacity:,} d'ici l'expiration."
                    ),
                )
            )
            entry[1] -= qty
            remaining -= qty
        if len(transfers) >= max_transfers:
            break
    return transfers
