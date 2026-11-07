"""The full natal chart: every computation in the spec, in one pure function."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from pathlib import Path

from . import __version__
from . import analysis as A
from .aspects import ORBS, Aspect, compute_aspects
from .ephemeris import COVERAGE, ephe_path
from .houses import Houses, HouseSystem, PointHouse, compute_houses, place_points
from .lots import Lot, compute_lots
from .patterns import LunarPhase, Pattern, aspect_patterns, lunar_phase, stelliums
from .points import PointsResult, compute_points
from .profections import ProfectionYear, profections
from .sect import Sect, compute_sect
from .timeutil import TZDATA_VERSION, UtcConversion, local_to_utc
from .transits import Transits, compute_transits, targets


@dataclass(frozen=True)
class Analysis:
    sect_roles: A.SectRoles
    dignities: tuple[A.Dignity, ...]
    dispositors: A.Dispositors
    mutual_receptions: tuple[A.MutualReception, ...]
    house_rulers: tuple[A.HouseRuler, ...]
    chart_ruler: A.ChartRuler
    lunar_phase: LunarPhase
    patterns: tuple[Pattern, ...]
    stelliums: tuple[Pattern, ...]


@dataclass(frozen=True)
class NatalChart:
    birth: UtcConversion
    latitude: float
    longitude: float
    points: PointsResult
    houses: Houses
    point_houses: tuple[PointHouse, ...]
    sect: Sect
    lots: tuple[Lot, ...]
    aspects: tuple[Aspect, ...]
    analysis: Analysis
    profections: tuple[ProfectionYear, ...]
    transits: Transits
    flags: tuple[str, ...]  # every flag raised anywhere in the chart
    evidence: tuple[str, ...]  # every evidence ID, in output order
    computation: dict


def _collect(obj, name: str) -> list[str]:
    """All values of fields called `name` (strings or tuples of strings), depth first."""
    found: list[str] = []
    if is_dataclass(obj):
        for f in fields(obj):
            value = getattr(obj, f.name)
            if f.name == name and isinstance(value, str):
                found.append(value)
            elif f.name == name and isinstance(value, tuple):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(_collect(value, name))
    elif isinstance(obj, (tuple, list)):
        for item in obj:
            found.extend(_collect(item, name))
    return found


def natal_chart(
    local: datetime,
    lat: float,
    lon: float,
    house_system: HouseSystem,
    now: datetime,
    fold: int = 0,
    ephe: Path | None = None,
) -> NatalChart:
    """`local` is the naive local birth time; `now` (UTC) anchors transits and profections."""
    birth = local_to_utc(local, lat, lon, fold)
    jd = birth.julian_day_ut
    points = compute_points(jd, ephe)
    houses = compute_houses(jd, lat, lon, house_system)
    sun = next(p for p in points.points if p.id == "sun")
    sect = compute_sect(jd, lat, lon, sun, houses.angle("asc").longitude)
    lots = compute_lots(points.points, houses, sect)
    aspects = compute_aspects(points.points, houses, lots)
    point_houses = place_points(points.points, houses)
    chart_ruler = A.chart_ruler(points.points, houses)
    analysis = Analysis(
        sect_roles=A.sect_roles(sect),
        dignities=A.dignities(points.points),
        dispositors=A.dispositors(points.points),
        mutual_receptions=A.mutual_receptions(points.points),
        house_rulers=A.house_rulers(points.points, houses),
        chart_ruler=chart_ruler,
        lunar_phase=lunar_phase(points.points),
        patterns=aspect_patterns(aspects),
        stelliums=stelliums(points.points, point_houses),
    )
    years = profections(local.date(), now.date(), houses)
    transits = compute_transits(targets(points.points, houses, chart_ruler, years[0]), now, ephe)

    parts = (points, houses, point_houses, sect, lots, aspects, analysis, years, transits)
    flags = tuple(dict.fromkeys(list(birth.flags) + _collect(parts, "flags")))
    evidence = tuple(dict.fromkeys(_collect(parts, "evidence")))
    computation = {
        "engine_version": __version__,
        "ephemeris": {"path": str(ephe or ephe_path()), "coverage": COVERAGE},
        "skipped_points": [s.id for s in points.skipped],
        "tzdata": TZDATA_VERSION,
        "zodiac": "tropical",
        "house_system_requested": houses.requested.value,
        "house_system_used": houses.system.value,
        "sect_method": "Sun's true altitude above the horizon",
        "orbs": ORBS,
        "lots": {lot.id: lot.formula for lot in lots},
        "profections": "whole sign from the ASC, age 0 = 1st house",
        "now": now.isoformat(),
    }
    return NatalChart(
        birth,
        lat,
        lon,
        points,
        houses,
        point_houses,
        sect,
        lots,
        aspects,
        analysis,
        years,
        transits,
        flags,
        evidence,
        computation,
    )
