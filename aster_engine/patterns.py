"""Lunar phase and aspect patterns (spec COMPUTATION step 5)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from .analysis import PLANETS
from .aspects import Aspect
from .houses import PointHouse
from .points import Point
from .zodiac import norm

LUNAR_PHASES = (
    "new",
    "crescent",
    "first_quarter",
    "gibbous",
    "full",
    "disseminating",
    "last_quarter",
    "balsamic",
)


@dataclass(frozen=True)
class LunarPhase:
    phase: str
    elongation: float  # norm(Moon - Sun), degrees
    waxing: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Pattern:
    kind: str  # grand_trine, t_square, grand_cross, kite, yod, stellium_sign, stellium_house
    planets: tuple[str, ...]  # in PLANETS order
    apex: str | None  # T-Square and Yod apex, Kite tail; else None
    where: str | None  # stellium sign or house number; else None
    evidence: tuple[str, ...]


def lunar_phase(points: tuple[Point, ...]) -> LunarPhase:
    lon = {p.id: p.longitude for p in points}
    elongation = norm(lon["moon"] - lon["sun"])
    phase = LUNAR_PHASES[int(elongation // 45)]
    return LunarPhase(phase, elongation, elongation < 180, (f"lunar_phase_{phase}",))


def _ordered(*planets: str) -> tuple[str, ...]:
    return tuple(sorted(planets, key=PLANETS.index))


def aspect_patterns(aspects: tuple[Aspect, ...]) -> tuple[Pattern, ...]:
    """Patterns among Sun to Pluto, from the step 4 aspects (same orbs)."""
    kind_of: dict[frozenset, str] = {
        frozenset((x.a, x.b)): x.aspect for x in aspects if x.a in PLANETS and x.b in PLANETS
    }

    def has(a: str, b: str, aspect: str) -> bool:
        return kind_of.get(frozenset((a, b))) == aspect

    found: list[Pattern] = []
    trines = []
    for a, b, c in combinations(PLANETS, 3):
        if has(a, b, "trine") and has(b, c, "trine") and has(a, c, "trine"):
            trines.append((a, b, c))
            found.append(_pattern("grand_trine", (a, b, c)))
    for a, b, c in combinations(PLANETS, 3):
        for x, y, apex in ((a, b, c), (a, c, b), (b, c, a)):
            if has(x, y, "opposition") and has(x, apex, "square") and has(y, apex, "square"):
                found.append(_pattern("t_square", (x, y, apex), apex))
            if has(x, y, "sextile") and has(x, apex, "quincunx") and has(y, apex, "quincunx"):
                found.append(_pattern("yod", (x, y, apex), apex))
    for a, b, c, d in combinations(PLANETS, 4):
        # Two oppositions, with each planet square both ends of the other.
        for (p, q), (r, s) in (((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))):
            if (
                has(p, q, "opposition")
                and has(r, s, "opposition")
                and all(has(x, y, "square") for x in (p, q) for y in (r, s))
            ):
                found.append(_pattern("grand_cross", (a, b, c, d)))
    for trine in trines:
        for tail in PLANETS:
            if tail in trine:
                continue
            for i, opposite in enumerate(trine):
                others = [t for j, t in enumerate(trine) if j != i]
                if has(tail, opposite, "opposition") and all(
                    has(tail, o, "sextile") for o in others
                ):
                    found.append(_pattern("kite", (*trine, tail), tail))
    return tuple(found)


def _pattern(kind: str, planets: tuple[str, ...], apex: str | None = None) -> Pattern:
    ordered = _ordered(*planets)
    if apex:
        rest = _ordered(*(p for p in planets if p != apex))
        label = "tail" if kind == "kite" else "apex"
        evidence = f"{kind}_{'_'.join(rest)}_{label}_{apex}"
    else:
        evidence = f"{kind}_{'_'.join(ordered)}"
    return Pattern(kind, ordered, apex, None, (evidence,))


def stelliums(points: tuple[Point, ...], houses: tuple[PointHouse, ...]) -> tuple[Pattern, ...]:
    """3 or more planets (Sun to Pluto) in one sign, and separately in one house."""
    by_sign, by_house = defaultdict(list), defaultdict(list)
    for p in points:
        if p.id in PLANETS:
            by_sign[p.position.sign].append(p.id)
    for ph in houses:
        if ph.id in PLANETS:
            by_house[ph.house].append(ph.id)
    result = []
    for sign, planets in by_sign.items():
        if len(planets) >= 3:
            ev = (f"stellium_sign_{sign}",)
            result.append(Pattern("stellium_sign", _ordered(*planets), None, sign, ev))
    for house, planets in sorted(by_house.items()):
        if len(planets) >= 3:
            ev = (f"stellium_house_{house}",)
            result.append(Pattern("stellium_house", _ordered(*planets), None, str(house), ev))
    return tuple(result)
