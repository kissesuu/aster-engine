"""Planets and points of the natal chart (spec COMPUTATION step 3)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .ephemeris import REQUIRED_FILES, EphemerisFileMissing, calc_body
from .zodiac import SignPosition, norm, sign_position

# (output id, ephemeris body id), in output order. The South Node has no
# ephemeris body of its own: it is the point opposite the North Node.
POINTS = (
    ("sun", "sun"),
    ("moon", "moon"),
    ("mercury", "mercury"),
    ("venus", "venus"),
    ("mars", "mars"),
    ("jupiter", "jupiter"),
    ("saturn", "saturn"),
    ("uranus", "uranus"),
    ("neptune", "neptune"),
    ("pluto", "pluto"),
    ("north_node", "mean_node"),
    ("south_node", "mean_node"),
    ("chiron", "chiron"),
    ("ceres", "ceres"),
    ("pallas", "pallas"),
    ("juno", "juno"),
    ("vesta", "vesta"),
    ("hygiea", "hygiea"),
    ("lilith", "lilith"),
    ("cupido", "cupido"),
)


# Days from birth within which an exact station makes a planet stationary.
STATION_WINDOWS = {
    "mercury": 2,
    "venus": 3,
    "mars": 3,
    "jupiter": 5,
    "saturn": 5,
    "uranus": 7,
    "neptune": 7,
    "pluto": 7,
}


@dataclass(frozen=True)
class Station:
    kind: str  # "stationary_direct" (retrograde -> direct) or "stationary_retrograde"
    jd_ut: float  # exact station, when the speed in longitude is 0
    days_from_birth: float  # station minus birth; negative when before birth


@dataclass(frozen=True)
class Point:
    id: str
    longitude: float
    latitude: float
    speed: float  # degrees per day in longitude
    position: SignPosition
    retrograde: bool
    station: Station | None
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SkippedPoint:
    id: str
    missing_file: str
    reason: str


@dataclass(frozen=True)
class PointsResult:
    points: tuple[Point, ...]
    skipped: tuple[SkippedPoint, ...]


def _speed(jd_ut: float, body: str, ephe: Path | None) -> float:
    return calc_body(jd_ut, body, ephe)[3]


def find_station(jd_ut: float, body: str, ephe: Path | None = None) -> Station | None:
    """The exact station nearest `jd_ut` within the body's window, if any."""
    window = STATION_WINDOWS.get(body)
    if window is None:
        return None
    # A retrograde loop lasts weeks, so a half-day scan cannot step over a
    # station, and at most one station falls inside any window.
    step = 0.5
    n = int(window / step)
    times = [jd_ut + i * step for i in range(-n, n + 1)]
    samples = [(t, _speed(t, body, ephe)) for t in times]
    found = []
    for (t0, v0), (t1, v1) in pairwise(samples):
        if (v0 < 0) == (v1 < 0):
            continue
        lo, hi, vlo = t0, t1, v0
        while hi - lo > 1e-6:  # about 0.1 s
            mid = (lo + hi) / 2
            vmid = _speed(mid, body, ephe)
            if (vmid < 0) == (vlo < 0):
                lo, vlo = mid, vmid
            else:
                hi = mid
        t = (lo + hi) / 2
        kind = "stationary_retrograde" if v0 >= 0 else "stationary_direct"
        found.append(Station(kind, t, t - jd_ut))
    found = [s for s in found if abs(s.days_from_birth) <= window]
    return min(found, key=lambda s: abs(s.days_from_birth), default=None)


def _point(id: str, lon: float, lat: float, speed: float, station: Station | None) -> Point:
    pos = sign_position(lon)
    retrograde = speed < 0
    evidence = [f"{id}_sign_{pos.sign}"]
    if retrograde:
        evidence.append(f"{id}_retrograde")
    if station:
        evidence.append(f"{id}_{station.kind}")
    return Point(id, norm(lon), lat, speed, pos, retrograde, station, tuple(evidence))


def compute_points(jd_ut: float, ephe: Path | None = None) -> PointsResult:
    """Tropical positions of every point at `jd_ut`.

    A point whose optional ephemeris file is missing, or does not cover the
    date, is skipped and reported. A missing required file (planets, Moon)
    raises EphemerisFileMissing: no chart is possible without it.
    """
    points, skipped = [], []
    for id, body in POINTS:
        try:
            lon, lat, _, speed, *_ = calc_body(jd_ut, body, ephe)
        except EphemerisFileMissing as e:
            if e.file in REQUIRED_FILES:
                raise
            skipped.append(SkippedPoint(id, e.file, str(e)))
            continue
        if id == "south_node":
            lon, lat = lon + 180, -lat
        points.append(_point(id, lon, lat, speed, find_station(jd_ut, body, ephe)))
    return PointsResult(tuple(points), tuple(skipped))
