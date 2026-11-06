"""Planets and points of the natal chart (spec COMPUTATION step 3)."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Point:
    id: str
    longitude: float
    latitude: float
    speed: float  # degrees per day in longitude
    position: SignPosition
    retrograde: bool
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


def _point(id: str, lon: float, lat: float, speed: float) -> Point:
    pos = sign_position(lon)
    retrograde = speed < 0
    evidence = [f"{id}_sign_{pos.sign}"]
    if retrograde:
        evidence.append(f"{id}_retrograde")
    return Point(id, norm(lon), lat, speed, pos, retrograde, tuple(evidence))


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
        points.append(_point(id, lon, lat, speed))
    return PointsResult(tuple(points), tuple(skipped))
