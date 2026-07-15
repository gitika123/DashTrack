"""Geospatial helpers for DashTrack (haversine, ETA, nearby search)."""
from __future__ import annotations

import math
from typing import Iterable, List, Tuple

EARTH_RADIUS_KM = 6371.0
AVG_DASHER_SPEED_KMH = 25.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def eta_minutes(distance_km: float, speed_kmh: float = AVG_DASHER_SPEED_KMH) -> int:
    if speed_kmh <= 0:
        return 0
    return max(1, int(math.ceil((distance_km / speed_kmh) * 60)))


def interpolate(
    lat1: float, lon1: float, lat2: float, lon2: float, t: float
) -> Tuple[float, float]:
    """Linear interpolation of coordinates; t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t


def nearby(
    origin_lat: float,
    origin_lon: float,
    points: Iterable[Tuple[str, float, float]],
    radius_km: float,
) -> List[Tuple[str, float]]:
    """Return (id, distance_km) within radius, sorted nearest-first."""
    scored = []
    for pid, lat, lon in points:
        d = haversine_km(origin_lat, origin_lon, lat, lon)
        if d <= radius_km:
            scored.append((pid, d))
    scored.sort(key=lambda x: x[1])
    return scored
