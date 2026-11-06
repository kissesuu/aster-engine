from itertools import combinations
from types import SimpleNamespace

import pytest
from reference import load_charts, local_datetime

from aster_engine.aspects import Factor, compute_aspects, find_aspect
from aster_engine.houses import HouseSystem, compute_houses, place_points
from aster_engine.lots import compute_lots
from aster_engine.patterns import aspect_patterns, lunar_phase, stelliums
from aster_engine.points import compute_points
from aster_engine.sect import compute_sect
from aster_engine.timeutil import local_to_utc

CHARTS = {c["birth"]["date"]: c for c in load_charts()}


def _chart(date):
    c = CHARTS[date]
    b = c["birth"]
    jd = local_to_utc(local_datetime(c), b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], HouseSystem.PLACIDUS)
    sun = next(p for p in points if p.id == "sun")
    sect = compute_sect(jd, b["lat"], b["lon"], sun, houses.angle("asc").longitude)
    aspects = compute_aspects(points, houses, compute_lots(points, houses, sect))
    return points, houses, aspects


def _aspects(**positions):
    """Aspects between planets placed at the given longitudes (not moving)."""
    fs = [Factor(id, lon, 0.0) for id, lon in positions.items()]
    return tuple(x for a, b in combinations(fs, 2) if (x := find_aspect(a, b)))


def _kinds(patterns):
    return {(p.kind, p.planets, p.apex) for p in patterns}


@pytest.mark.parametrize(
    "date,phase,waxing",
    [
        ("15 March 2000", "first_quarter", True),  # Moon 116° ahead of the Sun
        ("15 March 1990", "disseminating", False),  # 226°
        ("10 May 1943", "crescent", True),  # 63°
        ("1 June 1890", "gibbous", True),  # 152°
    ],
)
def test_lunar_phase(date, phase, waxing):
    lp = lunar_phase(_chart(date)[0])
    assert (lp.phase, lp.waxing) == (phase, waxing)
    assert lp.evidence == (f"lunar_phase_{phase}",)


def test_lunar_phase_boundaries():
    def phase(elongation):
        sun = SimpleNamespace(id="sun", longitude=100.0)
        moon = SimpleNamespace(id="moon", longitude=100.0 + elongation)
        return lunar_phase((sun, moon)).phase

    assert phase(0) == "new" and phase(44.99) == "new" and phase(45) == "crescent"
    assert phase(180) == "full" and phase(359.9) == "balsamic"


def test_t_square_cebu_1890():
    # Mars opposite Neptune (0.4°), both square Saturn (6.9° and 6.5°).
    patterns = aspect_patterns(_chart("1 June 1890")[2])
    assert _kinds(patterns) == {("t_square", ("mars", "saturn", "neptune"), "saturn")}
    assert patterns[0].evidence == ("t_square_mars_neptune_apex_saturn",)


def test_no_patterns_without_matching_aspects():
    assert aspect_patterns(_chart("15 March 2000")[2]) == ()


def test_grand_trine_and_kite():
    aspects = _aspects(sun=0, mars=120, jupiter=240, saturn=180)
    kinds = _kinds(aspect_patterns(aspects))
    assert ("grand_trine", ("sun", "mars", "jupiter"), None) in kinds
    # Saturn opposes the Sun and sextiles Mars and Jupiter.
    assert ("kite", ("sun", "mars", "jupiter", "saturn"), "saturn") in kinds


def test_grand_cross_includes_its_t_squares():
    patterns = aspect_patterns(_aspects(sun=0, mars=90, jupiter=180, saturn=270))
    kinds = _kinds(patterns)
    assert ("grand_cross", ("sun", "mars", "jupiter", "saturn"), None) in kinds
    assert sum(p.kind == "t_square" for p in patterns) == 4
    assert sum(p.kind == "grand_cross" for p in patterns) == 1


def test_yod():
    patterns = aspect_patterns(_aspects(venus=0, mars=60, pluto=210))
    assert _kinds(patterns) == {("yod", ("venus", "mars", "pluto"), "pluto")}
    assert patterns[0].evidence == ("yod_venus_mars_apex_pluto",)


def test_patterns_ignore_points():
    # Chiron would complete a Grand Trine, but only planets count.
    aspects = _aspects(sun=0, mars=120, chiron=240)
    assert aspect_patterns(aspects) == ()


def test_stelliums():
    points, houses, _ = _chart("15 March 2000")
    result = stelliums(points, place_points(points, houses))
    assert [(p.kind, p.planets, p.where) for p in result] == [
        ("stellium_sign", ("sun", "mercury", "venus"), "pisces"),
        ("stellium_house", ("sun", "mercury", "venus"), "8"),
    ]
    assert result[0].evidence == ("stellium_sign_pisces",)


def test_stelliums_tromso():
    c = CHARTS["1 December 1990"]
    b = c["birth"]
    jd = local_to_utc(local_datetime(c), b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], HouseSystem.PLACIDUS)  # Porphyry
    found = {(p.kind, p.where): p.planets for p in stelliums(points, place_points(points, houses))}
    assert found[("stellium_sign", "sagittarius")] == ("sun", "mercury", "venus")
    assert found[("stellium_sign", "capricorn")] == ("saturn", "uranus", "neptune")
    assert found[("stellium_house", "10")] == ("mercury", "venus", "saturn", "uranus", "neptune")
