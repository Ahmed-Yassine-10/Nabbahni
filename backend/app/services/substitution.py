"""Medication substitution engine (ATC + DDD based).

Builds candidate substitutions by matching medications that share ATC hierarchy
levels. Deeper shared prefixes imply stronger therapeutic equivalence:

  ATC5 (7 chars, e.g. J01CA04) — same chemical substance / DCI-equivalent
  ATC4 (5 chars, e.g. J01CA)   — same chemical subgroup
  ATC3 (4 chars, e.g. J01C)    — same pharmacological subgroup

DDD ratio lets a pharmacist reason about dose conversion. The engine only
proposes candidates; the pharmacist always validates the final decision.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import EquivalenceLevel


@dataclass
class MedLite:
    id: str
    atc_code: str
    dci: str
    ddd_value: float | None


@dataclass
class SubstitutionCandidate:
    source_id: str
    target_id: str
    atc_match_level: int
    equivalence: EquivalenceLevel
    ddd_ratio: float | None
    notes_fr: str


def _shared_atc_level(a: str, b: str) -> int:
    """Return the ATC depth (3,4,5) shared by two codes, else 0."""
    if len(a) >= 7 and len(b) >= 7 and a[:7] == b[:7]:
        return 5
    if len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]:
        return 4
    if len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4]:
        return 3
    return 0


_LEVEL_TO_EQUIV = {
    5: EquivalenceLevel.same_atc5,
    4: EquivalenceLevel.same_atc4,
    3: EquivalenceLevel.same_atc3,
}


def build_candidates(meds: list[MedLite], max_per_source: int = 6) -> list[SubstitutionCandidate]:
    """Generate substitution candidates across a medication list."""
    candidates: list[SubstitutionCandidate] = []

    for source in meds:
        scored: list[tuple[int, SubstitutionCandidate]] = []
        for target in meds:
            if target.id == source.id:
                continue
            level = _shared_atc_level(source.atc_code, target.atc_code)
            if level < 3:
                continue

            if level == 5 and source.dci.lower() == target.dci.lower():
                equiv = EquivalenceLevel.identical_dci
            else:
                equiv = _LEVEL_TO_EQUIV[level]

            ddd_ratio = None
            if source.ddd_value and target.ddd_value:
                ddd_ratio = round(float(source.ddd_value) / float(target.ddd_value), 3)

            notes = _note_for(equiv, ddd_ratio)
            scored.append(
                (
                    level,
                    SubstitutionCandidate(
                        source_id=source.id,
                        target_id=target.id,
                        atc_match_level=level,
                        equivalence=equiv,
                        ddd_ratio=ddd_ratio,
                        notes_fr=notes,
                    ),
                )
            )

        # Prefer the strongest matches per source.
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates.extend(c for _, c in scored[:max_per_source])

    return candidates


def _note_for(equiv: EquivalenceLevel, ddd_ratio: float | None) -> str:
    base = {
        EquivalenceLevel.identical_dci: "Même principe actif (DCI identique).",
        EquivalenceLevel.same_atc5: "Même substance chimique (ATC niveau 5).",
        EquivalenceLevel.same_atc4: "Même sous-groupe chimique (ATC niveau 4).",
        EquivalenceLevel.same_atc3: "Même sous-groupe pharmacologique (ATC niveau 3).",
    }[equiv]
    if ddd_ratio and abs(ddd_ratio - 1.0) > 0.01:
        base += f" Ratio DDD ≈ {ddd_ratio:g} (ajuster la posologie)."
    return base + " Validation du pharmacien requise."
