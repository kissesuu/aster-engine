"""Sect: day or night chart (spec COMPUTATION step 3)."""

from __future__ import annotations

from dataclasses import dataclass

import swisseph as swe

from .points import Point
from .zodiac import norm

# The Sun within this many degrees of the ASC or DSC makes the sect unstable.
UNSTABLE_ORB = 1.0


@dataclass(frozen=True)
class Sect:
    kind: str  # "day" or "night"
    sun_altitude: float  # true (geometric) altitude of the Sun, degrees
    sun_from_asc: float  # norm(Sun - ASC), degrees
    flags: tuple[str, ...]
    evidence: tuple[str, ...]


def sun_altitude(jd_ut: float, lat: float, lon: float, sun: Point) -> float:
    """True altitude of the Sun's center above the horizon, without refraction."""
    _, true_alt, _ = swe.azalt(
        jd_ut, swe.ECL2HOR, (lon, lat, 0.0), 0.0, 0.0, (sun.longitude, sun.latitude, 1.0)
    )
    return true_alt


def compute_sect(jd_ut: float, lat: float, lon: float, sun: Point, asc: float) -> Sect:
    """Day chart when the Sun is above the horizon, else night.

    Outside polar latitudes this agrees with norm(Sun - ASC) > 180°. Where the
    two disagree (the ASC and DSC swap near the poles), the altitude decides and
    the result is flagged.
    """
    altitude = sun_altitude(jd_ut, lat, lon, sun)
    from_asc = norm(sun.longitude - asc)
    day = altitude > 0
    flags = []
    # Distance from the ASC (0°) or DSC (180°) along the ecliptic.
    if min(from_asc, 360 - from_asc, abs(from_asc - 180)) <= UNSTABLE_ORB:
        flags.append("sect_unstable_sun_near_horizon")
    if day != (from_asc > 180):
        flags.append("sect_formula_disagrees_high_latitude")
    kind = "day" if day else "night"
    return Sect(kind, altitude, from_asc, tuple(flags), (f"sect_{kind}",))
