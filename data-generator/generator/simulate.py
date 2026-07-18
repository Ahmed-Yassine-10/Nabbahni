"""Demand + supply simulation primitives for the synthetic dataset."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta


# ── Seasonality: multiplicative factor by ATC group and day-of-year ──
def seasonal_factor(atc_code: str, day: date) -> float:
    doy = day.timetuple().tm_yday
    # Winter (respiratory/antibiotics) peak around Dec–Feb.
    winter = 1.0 + 0.35 * math.cos(2 * math.pi * (doy - 15) / 365)
    # Summer (rehydration/digestive) peak around Jul–Aug.
    summer = 1.0 + 0.25 * math.cos(2 * math.pi * (doy - 200) / 365)

    group = atc_code[0]
    if group in ("J", "R"):          # anti-infectives, respiratory
        return max(0.5, winter)
    if group == "A":                  # digestive/metabolism
        return max(0.6, 0.5 * summer + 0.5)
    if group == "N":                  # CNS — mild winter effect
        return max(0.7, 0.7 + 0.3 * (winter - 1) + 1) / 1.3
    return 1.0                         # chronic meds ~ flat


def weekday_factor(day: date) -> float:
    # Pharmacies busier early week; Sunday quieter in Tunisia.
    return {0: 1.15, 1: 1.10, 2: 1.05, 3: 1.05, 4: 1.10, 5: 0.95, 6: 0.70}[day.weekday()]


def ramadan_factor(day: date) -> float:
    """Rough Ramadan windows (shifted) → altered consumption patterns."""
    # Approximate Ramadan start dates for 2024/2025/2026.
    windows = [
        (date(2024, 3, 11), date(2024, 4, 9)),
        (date(2025, 3, 1), date(2025, 3, 30)),
        (date(2026, 2, 18), date(2026, 3, 19)),
    ]
    for start, end in windows:
        if start <= day <= end:
            return 1.2   # more OTC/digestive, shifted timing
    return 1.0


@dataclass
class MedProfile:
    med_id: str
    atc_code: str
    base_daily_per_100k: float   # baseline units/day per 100k population
    trend_per_year: float        # multiplicative annual trend (e.g. 1.05 = +5%/yr)
    is_essential: bool


def base_demand(profile: MedProfile, population: int, day: date, day_index: int,
                total_days: int, rng: random.Random) -> float:
    base = profile.base_daily_per_100k * (population / 100_000)
    trend = profile.trend_per_year ** (day_index / 365.0)
    season = seasonal_factor(profile.atc_code, day)
    wk = weekday_factor(day)
    ram = ramadan_factor(day)
    noise = rng.gauss(1.0, 0.15)
    return max(0.0, base * trend * season * wk * ram * noise)


@dataclass
class ShortageEpisode:
    med_id: str
    governorate_id: str | None
    start: date
    end: date
    cause: str


def build_shortage_episodes(
    med_ids: list[str], gov_ids: list[str], start: date, days: int, rng: random.Random,
    n_episodes: int = 25,
) -> list[ShortageEpisode]:
    causes = [
        "Retard fournisseur",
        "Rupture matière première",
        "Congestion portuaire (Radès)",
        "Pic de demande saisonnier",
        "Retrait de lot",
        "Hausse des prix à l'importation",
    ]
    episodes: list[ShortageEpisode] = []

    # Historical (resolved) episodes across the training window.
    for _ in range(n_episodes):
        med = rng.choice(med_ids)
        offset = rng.randint(30, max(31, days - 90))
        length = rng.randint(14, 45)
        s = start + timedelta(days=offset)
        e = s + timedelta(days=length)
        gov = rng.choice(gov_ids) if rng.random() < 0.5 else None  # some national
        episodes.append(ShortageEpisode(med, gov, s, e, rng.choice(causes)))

    # Ongoing episodes that span "today" — these drive the live risk map,
    # recommendations, and alerts. Regional and spread across distinct
    # governorates so the heatmap shows genuine variety (some governorates at
    # high risk, others normal). Recommendations still fire from the
    # per-medication worst governorate, so national action is captured too.
    n_current = max(12, n_episodes // 2)
    current_meds = rng.sample(med_ids, min(n_current, len(med_ids)))
    shuffled_govs = gov_ids[:]
    rng.shuffle(shuffled_govs)
    for i, med in enumerate(current_meds):
        s = start + timedelta(days=rng.randint(days - 45, days - 10))
        e = start + timedelta(days=days + rng.randint(10, 60))  # extends past today
        # Assign 1-3 affected governorates per medication, spread around.
        n_govs = rng.randint(1, 3)
        for j in range(n_govs):
            gov = shuffled_govs[(i + j) % len(shuffled_govs)]
            episodes.append(ShortageEpisode(med, gov, s, e, rng.choice(causes)))

    return episodes


def in_episode(episodes: list[ShortageEpisode], med_id: str, gov_id: str, day: date) -> bool:
    for ep in episodes:
        if ep.med_id != med_id:
            continue
        if ep.governorate_id not in (None, gov_id):
            continue
        if ep.start <= day <= ep.end:
            return True
    return False
