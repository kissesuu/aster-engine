"""Houses and angles (spec COMPUTATION step 3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import swisseph as swe

from .points import Point
from .zodiac import SIGNS, SignPosition, norm, sign_position


class HouseSystem(StrEnum):
    PLACIDUS = "placidus"
    WHOLE_SIGN = "whole_sign"
    PORPHYRY = "porphyry"  # only as the fallback when Placidus fails


@dataclass(frozen=True)
class Angle:
    id: str  # "asc", "mc", "dsc", "ic", "vertex"
    longitude: float
    position: SignPosition
    house: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Houses:
    requested: HouseSystem
    system: HouseSystem  # the system actually used
    cusps: tuple[float, ...]  # cusps[0] is house 1
    angles: tuple[Angle, ...]
    flags: tuple[str, ...]  # "placidus_unavailable_high_latitude"
    evidence: tuple[str, ...]  # house_1_sign_leo, ...

    def angle(self, id: str) -> Angle:
        return next(a for a in self.angles if a.id == id)


@dataclass(frozen=True)
class PointHouse:
    id: str
    house: int
    evidence: str  # e.g. "sun_house_10"


def whole_sign_cusps(asc: float) -> tuple[float, ...]:
    """House n starts at 0° of the n-th sign counted from the ASC sign."""
    first = int(norm(asc) // 30) * 30
    return tuple(norm(first + 30 * i) for i in range(12))


def house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    """House (1-12) containing `longitude`; a point exactly on a cusp is in that house."""
    lon = norm(longitude)
    for i in range(12):
        start, end = cusps[i], cusps[(i + 1) % 12]
        if norm(lon - start) < norm(end - start):
            return i + 1
    raise ValueError("cusps do not cover the zodiac")  # unreachable for valid cusps


def compute_houses(jd_ut: float, lat: float, lon: float, system: HouseSystem) -> Houses:
    """Cusps and angles for the birth time and place.

    When Placidus cannot be computed (high latitude), the result is flagged
    and Porphyry, a quadrant system that always works, is used instead. ASC,
    MC and Vertex do not depend on the house system.
    """
    flags = []
    used = system
    if system is HouseSystem.PLACIDUS:
        try:
            cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"P")
        except swe.Error:
            flags.append("placidus_unavailable_high_latitude")
            used = HouseSystem.PORPHYRY
    if used is not HouseSystem.PLACIDUS:
        # Porphyry is always computable and gives the same ASC, MC and Vertex.
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"O")
    asc, mc, vertex = ascmc[0], ascmc[1], ascmc[3]
    if used is HouseSystem.WHOLE_SIGN:
        cusps = whole_sign_cusps(asc)
    cusps = [norm(c) for c in cusps]
    if used is not HouseSystem.WHOLE_SIGN:
        # Use the exact angle values for the angular cusps, so each angle
        # always falls in its own house despite float rounding.
        cusps[0], cusps[3], cusps[6], cusps[9] = (norm(x) for x in (asc, mc + 180, asc + 180, mc))
    cusps = tuple(cusps)

    angles = []
    for id, angle_lon in (
        ("asc", asc),
        ("mc", mc),
        ("dsc", asc + 180),
        ("ic", mc + 180),
        ("vertex", vertex),
    ):
        pos = sign_position(angle_lon)
        house = house_of(angle_lon, cusps)
        evidence = [f"{id}_sign_{pos.sign}"]
        if id == "vertex":
            evidence.append(f"vertex_house_{house}")
        angles.append(Angle(id, norm(angle_lon), pos, house, tuple(evidence)))

    cusp_evidence = tuple(f"house_{i + 1}_sign_{SIGNS[int(c // 30)]}" for i, c in enumerate(cusps))
    return Houses(system, used, cusps, tuple(angles), tuple(flags), cusp_evidence)


def place_points(points: tuple[Point, ...], houses: Houses) -> tuple[PointHouse, ...]:
    """The house of each point, in the house system actually used."""
    result = []
    for p in points:
        house = house_of(p.longitude, houses.cusps)
        result.append(PointHouse(p.id, house, f"{p.id}_house_{house}"))
    return tuple(result)
