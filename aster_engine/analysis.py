"""Technical analysis: sect roles, dignities, dispositors, receptions and house
rulers (spec COMPUTATION step 5)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .houses import Houses, house_of
from .points import Point
from .sect import Sect
from .zodiac import SIGNS, TRADITIONAL_RULERS, sign_position

TRADITIONAL_PLANETS = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")
PLANETS = TRADITIONAL_PLANETS + ("uranus", "neptune", "pluto")

DOMICILES = {
    p: tuple(s for s, ruler in TRADITIONAL_RULERS.items() if ruler == p)
    for p in TRADITIONAL_PLANETS
}
EXALTATIONS = {
    "sun": "aries",
    "moon": "taurus",
    "mercury": "virgo",
    "venus": "pisces",
    "mars": "capricorn",
    "jupiter": "cancer",
    "saturn": "libra",
}


def _opposite(sign: str) -> str:
    return SIGNS[(SIGNS.index(sign) + 6) % 12]


DETRIMENTS = {p: tuple(_opposite(s) for s in signs) for p, signs in DOMICILES.items()}
FALLS = {p: _opposite(s) for p, s in EXALTATIONS.items()}


@dataclass(frozen=True)
class SectRoles:
    sect_light: str
    benefic_of_sect: str
    malefic_of_sect: str
    benefic_contrary_to_sect: str
    malefic_contrary_to_sect: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Dignity:
    planet: str
    sign: str
    dignities: tuple[str, ...]  # any of domicile, exaltation, detriment, fall
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Disposition:
    planet: str
    dispositor: str
    chain: tuple[str, ...]  # planet, its dispositor, ... up to the end or the loop


@dataclass(frozen=True)
class Dispositors:
    dispositions: tuple[Disposition, ...]
    final_dispositors: tuple[str, ...]  # planets in their own domicile
    loops: tuple[tuple[str, ...], ...]  # each loop starts at its first planet in PLANETS order
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class MutualReception:
    a: str
    b: str
    kinds: tuple[str, ...]  # "domicile", "exaltation", "mixed"
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class HouseRuler:
    house: int
    sign: str  # sign on the cusp
    ruler: str
    ruler_house: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ChartRuler:
    planet: str
    house: int
    evidence: tuple[str, ...]


def sect_roles(sect: Sect) -> SectRoles:
    if sect.kind == "day":
        light, benefic, malefic, contrary_b, contrary_m = (
            "sun",
            "jupiter",
            "saturn",
            "venus",
            "mars",
        )
    else:
        light, benefic, malefic, contrary_b, contrary_m = (
            "moon",
            "venus",
            "mars",
            "jupiter",
            "saturn",
        )
    evidence = (
        f"sect_light_{light}",
        f"benefic_of_sect_{benefic}",
        f"malefic_of_sect_{malefic}",
        f"benefic_contrary_to_sect_{contrary_b}",
        f"malefic_contrary_to_sect_{contrary_m}",
    )
    return SectRoles(light, benefic, malefic, contrary_b, contrary_m, evidence)


def _signs(points: tuple[Point, ...]) -> dict[str, str]:
    return {p.id: p.position.sign for p in points if p.id in PLANETS}


def dignities(points: tuple[Point, ...]) -> tuple[Dignity, ...]:
    signs = _signs(points)
    result = []
    for planet in TRADITIONAL_PLANETS:
        sign = signs[planet]
        found = []
        if sign in DOMICILES[planet]:
            found.append("domicile")
        if sign == EXALTATIONS[planet]:
            found.append("exaltation")
        if sign in DETRIMENTS[planet]:
            found.append("detriment")
        if sign == FALLS[planet]:
            found.append("fall")
        evidence = tuple(f"{planet}_{d}" for d in found)
        result.append(Dignity(planet, sign, tuple(found), evidence))
    return tuple(result)


def dispositors(points: tuple[Point, ...]) -> Dispositors:
    signs = _signs(points)
    ruler = {p: TRADITIONAL_RULERS[signs[p]] for p in PLANETS}
    dispositions, loops = [], set()
    for planet in PLANETS:
        chain = [planet]
        while ruler[chain[-1]] not in chain:
            chain.append(ruler[chain[-1]])
        start = chain.index(ruler[chain[-1]])
        cycle = chain[start:]
        if len(cycle) > 1:
            first = min(cycle, key=PLANETS.index)
            i = cycle.index(first)
            loops.add(tuple(cycle[i:] + cycle[:i]))
        dispositions.append(Disposition(planet, ruler[planet], tuple(chain)))
    finals = tuple(p for p in TRADITIONAL_PLANETS if ruler[p] == p)
    loops_sorted = tuple(sorted(loops, key=lambda loop: PLANETS.index(loop[0])))
    evidence = tuple(f"final_dispositor_{p}" for p in finals) + tuple(
        "dispositor_loop_" + "_".join(loop) for loop in loops_sorted
    )
    return Dispositors(tuple(dispositions), finals, loops_sorted, evidence)


def _receives(host: str, sign: str) -> tuple[str, ...]:
    """How `host` receives a planet in `sign`: by domicile and/or exaltation."""
    ways = []
    if sign in DOMICILES[host]:
        ways.append("domicile")
    if sign == EXALTATIONS[host]:
        ways.append("exaltation")
    return tuple(ways)


def mutual_receptions(points: tuple[Point, ...]) -> tuple[MutualReception, ...]:
    signs = _signs(points)
    result = []
    for a, b in combinations(TRADITIONAL_PLANETS, 2):
        a_by_b = _receives(b, signs[a])  # b receives a
        b_by_a = _receives(a, signs[b])
        kinds = []
        for x in a_by_b:
            for y in b_by_a:
                kind = x if x == y else "mixed"
                if kind not in kinds:
                    kinds.append(kind)
        if kinds:
            evidence = tuple(f"{a}_{b}_mutual_reception_{k}" for k in kinds)
            result.append(MutualReception(a, b, tuple(kinds), evidence))
    return tuple(result)


def house_rulers(points: tuple[Point, ...], houses: Houses) -> tuple[HouseRuler, ...]:
    lon = {p.id: p.longitude for p in points}
    result = []
    for i, cusp in enumerate(houses.cusps):
        sign = sign_position(cusp).sign
        ruler = TRADITIONAL_RULERS[sign]
        ruler_house = house_of(lon[ruler], houses.cusps)
        evidence = (f"house_{i + 1}_ruler_{ruler}", f"house_{i + 1}_ruler_in_house_{ruler_house}")
        result.append(HouseRuler(i + 1, sign, ruler, ruler_house, evidence))
    return tuple(result)


def chart_ruler(points: tuple[Point, ...], houses: Houses) -> ChartRuler:
    planet = TRADITIONAL_RULERS[houses.angle("asc").position.sign]
    lon = next(p.longitude for p in points if p.id == planet)
    house = house_of(lon, houses.cusps)
    return ChartRuler(planet, house, (f"chart_ruler_{planet}", f"chart_ruler_in_house_{house}"))
