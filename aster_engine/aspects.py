"""Aspects between natal factors (spec COMPUTATION step 4)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .houses import Houses
from .lots import Lot
from .points import Point
from .zodiac import SIGNS, sign_position

ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "quincunx": 150,
    "opposition": 180,
}

# Maximum orb per category and aspect, in degrees.
ORBS = {
    "planet": {
        "conjunction": 8,
        "opposition": 8,
        "square": 7,
        "trine": 7,
        "sextile": 5,
        "quincunx": 3,
    },
    "luminary": {
        "conjunction": 10,
        "opposition": 10,
        "square": 8,
        "trine": 8,
        "sextile": 6,
        "quincunx": 3,
    },
    "angle": {
        "conjunction": 5,
        "opposition": 5,
        "square": 5,
        "trine": 5,
        "sextile": 3,
        "quincunx": 1.5,
    },
    "point": {
        "conjunction": 3,
        "opposition": 3,
        "square": 3,
        "trine": 3,
        "sextile": 3,
        "quincunx": 1.5,
    },
}

LUMINARIES = {"sun", "moon"}
PLANETS = {"mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"}
ANGLES = {"asc", "mc"}


@dataclass(frozen=True)
class Factor:
    id: str
    longitude: float
    speed: float  # degrees per day; 0 for factors treated as fixed

    @property
    def category(self) -> str:
        if self.id in LUMINARIES:
            return "luminary"
        if self.id in PLANETS:
            return "planet"
        if self.id in ANGLES:
            return "angle"
        return "point"


@dataclass(frozen=True)
class Aspect:
    a: str
    b: str
    aspect: str
    orb: float  # exact distance from the exact aspect, degrees
    max_orb: float
    applying: bool  # False: separating
    out_of_sign: bool
    evidence: tuple[str, ...]


def max_orb(a: Factor, b: Factor, aspect: str) -> float:
    """The spec's orb for a pair: a point or an angle caps the orb; otherwise
    the larger of the two (Sun/Moon over planets)."""
    cats = {a.category, b.category}
    for cat in ("point", "angle", "luminary"):
        if cat in cats:
            return ORBS[cat][aspect]
    return ORBS["planet"][aspect]


def _separation(x: float, y: float) -> float:
    return abs((x - y + 180) % 360 - 180)


def _sign_distance(x: float, y: float) -> int:
    d = (SIGNS.index(sign_position(x).sign) - SIGNS.index(sign_position(y).sign)) % 12
    return min(d, 12 - d)


def find_aspect(a: Factor, b: Factor, aspects=ASPECTS) -> Aspect | None:
    sep = _separation(a.longitude, b.longitude)
    best = None
    for name, angle in aspects.items():
        orb = abs(sep - angle)
        limit = max_orb(a, b, name)
        if orb <= limit and (best is None or orb < best[1]):
            best = (name, orb, limit)
    if best is None:
        return None
    name, orb, limit = best
    # Applying when the orb shrinks over the next moment of motion.
    h = 1 / 1440
    later = _separation(a.longitude + a.speed * h, b.longitude + b.speed * h)
    applying = abs(later - ASPECTS[name]) < orb
    out_of_sign = _sign_distance(a.longitude, b.longitude) * 30 != ASPECTS[name]
    evidence = [f"{a.id}_{b.id}_{name}"]
    if out_of_sign:
        evidence.append(f"{a.id}_{b.id}_{name}_out_of_sign")
    return Aspect(a.id, b.id, name, orb, limit, applying, out_of_sign, tuple(evidence))


def factors(points: tuple[Point, ...], houses: Houses, lots: tuple[Lot, ...]) -> list[Factor]:
    """Everything that takes part in aspects, in output order.

    ASC and MC move with their actual motion; Vertex and Lots are treated as
    fixed, as Astro.com does. DSC and IC are left out: their aspects mirror
    those of the ASC and MC.
    """
    result = [Factor(p.id, p.longitude, p.speed) for p in points]
    for id in ("asc", "mc"):
        angle = houses.angle(id)
        result.append(Factor(id, angle.longitude, angle.speed))
    result.append(Factor("vertex", houses.angle("vertex").longitude, 0.0))
    result.extend(Factor(lot.id, lot.longitude, 0.0) for lot in lots)
    return result


def compute_aspects(
    points: tuple[Point, ...], houses: Houses, lots: tuple[Lot, ...]
) -> tuple[Aspect, ...]:
    """Every aspect within orb, each pair ordered as in `factors`."""
    result = []
    for a, b in combinations(factors(points, houses, lots), 2):
        ids = {a.id, b.id}
        if ids <= ANGLES or ids == {"north_node", "south_node"}:
            continue
        # South Node aspects other than the conjunction mirror the North Node's.
        allowed = {"conjunction": 0} if "south_node" in ids else ASPECTS
        aspect = find_aspect(a, b, allowed)
        if aspect:
            result.append(aspect)
    return tuple(result)
