"""Hermetic Lots (spec COMPUTATION step 3)."""

from __future__ import annotations

from dataclasses import dataclass

from .houses import Houses, house_of, whole_sign_cusps
from .points import Point
from .sect import Sect
from .zodiac import SIGNS, TRADITIONAL_RULERS, SignPosition, format_longitude, norm, sign_position


@dataclass(frozen=True)
class Lot:
    id: str  # "lot_fortune", "lot_spirit", "lot_victory", "lot_wealth"
    longitude: float
    position: SignPosition
    house: int  # in the chart's house system
    formula: str  # e.g. "day: ASC + Moon − Sun"
    calculation: str  # the formula with the values used
    evidence: tuple[str, ...]


def _lot(id, formula, terms, houses) -> Lot:
    """terms: [(sign, label, longitude)] where sign is +1 or -1; the first is ASC."""
    lon = norm(sum(s * x for s, _, x in terms))
    parts = []
    for i, (s, _, x) in enumerate(terms):
        value = format_longitude(x)
        parts.append(value if i == 0 else f"{'+' if s > 0 else '−'} {value}")
    pos = sign_position(lon)
    calculation = f"{' '.join(parts)} = {format_longitude(lon)} ({pos.sign})"
    house = house_of(lon, houses.cusps)
    evidence = (f"{id}_sign_{pos.sign}", f"{id}_house_{house}")
    return Lot(id, lon, pos, house, formula, calculation, evidence)


def compute_lots(points: tuple[Point, ...], houses: Houses, sect: Sect) -> tuple[Lot, ...]:
    """Fortune, Spirit, Victory and Wealth, all using the chart's one sect."""
    lon = {p.id: p.longitude for p in points}
    asc = houses.angle("asc").longitude
    day = sect.kind == "day"
    s = sect.kind

    def sect_lot(id, name_a, a, name_b, b):
        # Day: ASC + a − b; night: reversed.
        if not day:
            name_a, a, name_b, b = name_b, b, name_a, a
        terms = [(1, "ASC", asc), (1, name_a, a), (-1, name_b, b)]
        return _lot(id, f"{s}: ASC + {name_a} − {name_b}", terms, houses)

    fortune = sect_lot("lot_fortune", "Moon", lon["moon"], "Sun", lon["sun"])
    spirit = sect_lot("lot_spirit", "Sun", lon["sun"], "Moon", lon["moon"])
    victory = sect_lot("lot_victory", "Jupiter", lon["jupiter"], "Spirit", spirit.longitude)

    second_sign = SIGNS[(SIGNS.index(sign_position(asc).sign) + 1) % 12]
    ruler = TRADITIONAL_RULERS[second_sign]
    cusp = whole_sign_cusps(asc)[1]
    wealth = _lot(
        "lot_wealth",
        f"ASC + 2nd cusp (0° {second_sign.title()}, Whole Sign) − {ruler.title()}"
        f" (ruler of {second_sign.title()})",
        [(1, "ASC", asc), (1, "2nd cusp", cusp), (-1, ruler, lon[ruler])],
        houses,
    )
    return fortune, spirit, victory, wealth
