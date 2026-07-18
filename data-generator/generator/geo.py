"""Lightweight geometry helpers for the seeder.

Detailed governorate boundaries are out of scope for the synthetic dataset; we
generate a simplified convex polygon around each centroid so the national
choropleth renders distinct regions. Real boundary GeoJSON can be swapped in
later without schema changes.
"""
from __future__ import annotations

import math
import random


def _polygon_ring(lat: float, lon: float, radius_deg: float, rng: random.Random):
    points = []
    n = 6
    for i in range(n):
        angle = (2 * math.pi * i) / n
        jitter = 0.75 + rng.random() * 0.5
        r = radius_deg * jitter
        # Longitude scaled by latitude to look less distorted.
        px = lon + r * math.cos(angle) / max(0.3, math.cos(math.radians(lat)))
        py = lat + r * math.sin(angle)
        points.append([round(px, 5), round(py, 5)])
    points.append(points[0])
    return points


def simple_polygon_geojson(lat: float, lon: float, radius_deg: float, rng: random.Random) -> dict:
    """Build an irregular hexagon as a GeoJSON MultiPolygon around a centroid."""
    ring = _polygon_ring(lat, lon, radius_deg, rng)
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


# Simplified outline of Tunisia (lon, lat), convex enough to use as a clip
# region. Not survey-grade — it exists so the national choropleth tiles the
# country instead of showing detached blobs. Swap in official boundary
# GeoJSON when it is available; nothing else needs to change.
TUNISIA_OUTLINE: list[tuple[float, float]] = [
    (8.34, 36.95),   # north-west coast
    (9.10, 37.21),
    (9.80, 37.34),
    (10.30, 37.25),
    (10.75, 36.98),
    (11.05, 37.09),   # Cap Bon
    (11.16, 36.82),
    (10.85, 36.45),
    (10.60, 36.05),
    (10.85, 35.65),
    (11.05, 35.25),
    (11.12, 34.80),
    (10.55, 34.35),
    (10.10, 33.85),
    (10.35, 33.55),
    (11.05, 33.35),
    (11.55, 33.15),
    (11.50, 32.60),
    (10.60, 32.05),
    (10.15, 31.65),
    (9.70, 30.40),   # southern tip
    (9.05, 32.10),
    (8.35, 32.55),
    (7.90, 33.20),
    (7.55, 33.85),
    (8.25, 34.65),
    (8.30, 35.25),
    (8.25, 35.75),
    (8.60, 36.45),
]


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Monotone-chain convex hull, counter-clockwise."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _clip_polygon(
    subject: list[tuple[float, float]], clip: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Sutherland–Hodgman clipping of `subject` against a convex `clip` ring."""

    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def intersect(p1, p2, a, b):
        x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return p2
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    # Ensure the clip ring is counter-clockwise so `inside` has a consistent sign.
    area = sum(
        clip[i][0] * clip[(i + 1) % len(clip)][1]
        - clip[(i + 1) % len(clip)][0] * clip[i][1]
        for i in range(len(clip))
    )
    ring = clip if area > 0 else clip[::-1]

    output = list(subject)
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        if not output:
            return []
        current, output = output, []
        for j, p in enumerate(current):
            prev = current[j - 1]
            if inside(p, a, b):
                if not inside(prev, a, b):
                    output.append(intersect(prev, p, a, b))
                output.append(p)
            elif inside(prev, a, b):
                output.append(intersect(prev, p, a, b))
    return output


def voronoi_regions(
    centroids: list[tuple[float, float]],
    outline: list[tuple[float, float]] | None = None,
) -> list[dict]:
    """Tessellate the country into one region per centroid.

    Returns a GeoJSON MultiPolygon per input centroid, in the same order.
    Each governorate becomes a contiguous area rather than a floating shape,
    which is what makes the national heatmap readable as a map.

    `centroids` are (lon, lat) pairs. Falls back to `None` entries if SciPy is
    unavailable, letting the caller use the hexagon approximation instead.
    """
    try:
        import numpy as np
        from scipy.spatial import Voronoi
    except ImportError:  # pragma: no cover - optional dependency
        return [None] * len(centroids)  # type: ignore[list-item]

    # Sutherland–Hodgman requires a convex clip region, and the national
    # outline is not convex (Cap Bon, the southern tip). The hull is a close
    # enough envelope for a choropleth and keeps the clipping exact.
    clip = _convex_hull(list(outline or TUNISIA_OUTLINE))
    pts = np.array(centroids, dtype=float)

    # Mirror the point set far outside the map so every real cell is bounded;
    # otherwise the hull points get infinite Voronoi regions.
    # np.ptp(), not ndarray.ptp() — the method was removed in NumPy 2.
    span = max(float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1]))) or 1.0
    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
    far = np.array(
        [
            [cx - 100 * span, cy - 100 * span],
            [cx + 100 * span, cy - 100 * span],
            [cx - 100 * span, cy + 100 * span],
            [cx + 100 * span, cy + 100 * span],
        ]
    )
    vor = Voronoi(np.vstack([pts, far]))

    regions: list[dict] = []
    for i in range(len(centroids)):
        region_idx = vor.point_region[i]
        verts = vor.regions[region_idx]
        if not verts or -1 in verts:
            regions.append(None)  # type: ignore[arg-type]
            continue
        poly = [(float(vor.vertices[v][0]), float(vor.vertices[v][1])) for v in verts]
        clipped = _clip_polygon(poly, clip)
        if len(clipped) < 3:
            regions.append(None)  # type: ignore[arg-type]
            continue
        ring = [[round(x, 5), round(y, 5)] for x, y in clipped]
        ring.append(ring[0])
        regions.append({"type": "MultiPolygon", "coordinates": [[ring]]})
    return regions


def jitter_point(lat: float, lon: float, max_km: float, rng: random.Random) -> tuple[float, float]:
    """Return a random point within max_km of the given coordinate."""
    # ~111 km per degree latitude.
    dist_deg = (rng.random() ** 0.5) * (max_km / 111.0)
    bearing = rng.random() * 2 * math.pi
    dlat = dist_deg * math.cos(bearing)
    dlon = dist_deg * math.sin(bearing) / max(0.3, math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
