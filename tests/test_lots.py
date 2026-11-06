from datetime import datetime

import pytest
from reference import ANGLE_TOLERANCE, angle_diff, chart_id, load_charts, local_datetime

from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.lots import compute_lots
from aster_engine.points import compute_points
from aster_engine.sect import compute_sect
from aster_engine.timeutil import local_to_utc
from aster_engine.zodiac import SIGNS, TRADITIONAL_RULERS, norm

CHARTS = load_charts()


def _chart(chart, system=HouseSystem.PLACIDUS):
    b = chart["birth"]
    jd = local_to_utc(local_datetime(chart), b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], system)
    sun = next(p for p in points if p.id == "sun")
    sect = compute_sect(jd, b["lat"], b["lon"], sun, houses.angle("asc").longitude)
    lots = {lot.id: lot for lot in compute_lots(points, houses, sect)}
    return {p.id: p.longitude for p in points}, houses, sect, lots


def _by_date(date):
    return next(c for c in CHARTS if c["birth"]["date"] == date)


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_fortune_matches_astro_com(chart):
    _, _, _, lots = _chart(chart)
    ref = chart["bodies"]["lot_fortune"]
    assert abs(angle_diff(lots["lot_fortune"].longitude, ref["longitude"])) <= ANGLE_TOLERANCE
    assert lots["lot_fortune"].house == ref["house"]


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_sect_formulas(chart):
    lon, houses, sect, lots = _chart(chart)
    asc = houses.angle("asc").longitude
    sun, moon, jupiter = lon["sun"], lon["moon"], lon["jupiter"]
    spirit = lots["lot_spirit"].longitude
    if sect.kind == "day":
        expected = {
            "lot_fortune": asc + moon - sun,
            "lot_spirit": asc + sun - moon,
            "lot_victory": asc + jupiter - spirit,
        }
    else:
        expected = {
            "lot_fortune": asc + sun - moon,
            "lot_spirit": asc + moon - sun,
            "lot_victory": asc + spirit - jupiter,
        }
    for id, value in expected.items():
        assert lots[id].longitude == pytest.approx(norm(value), abs=1e-9), id
        assert lots[id].formula.startswith(f"{sect.kind}: ASC + ")


def test_day_chart_formula_strings():
    _, _, sect, lots = _chart(_by_date("15 March 2000"))
    assert sect.kind == "day"
    assert lots["lot_fortune"].formula == "day: ASC + Moon − Sun"
    assert lots["lot_spirit"].formula == "day: ASC + Sun − Moon"
    assert lots["lot_victory"].formula == "day: ASC + Jupiter − Spirit"
    assert lots["lot_fortune"].calculation.endswith("(sagittarius)")
    assert lots["lot_fortune"].evidence == ("lot_fortune_sign_sagittarius", "lot_fortune_house_4")


def test_night_chart_reverses_formulas():
    _, _, sect, lots = _chart(_by_date("15 March 1990"))
    assert sect.kind == "night"
    assert lots["lot_fortune"].formula == "night: ASC + Sun − Moon"
    assert lots["lot_spirit"].formula == "night: ASC + Moon − Sun"
    assert lots["lot_victory"].formula == "night: ASC + Spirit − Jupiter"


def test_wealth_uses_whole_sign_second_house_and_traditional_ruler():
    # Manila 2000: ASC 4° Leo, so the Whole Sign 2nd house is Virgo, ruled by Mercury.
    lon, houses, _, lots = _chart(_by_date("15 March 2000"))
    wealth = lots["lot_wealth"]
    asc = houses.angle("asc").longitude
    assert wealth.longitude == pytest.approx(norm(asc + 150 - lon["mercury"]), abs=1e-9)
    assert wealth.formula == "ASC + 2nd cusp (0° Virgo, Whole Sign) − Mercury (ruler of Virgo)"
    assert " + 150°00'00\" − " in wealth.calculation


@pytest.mark.parametrize("date", ["15 March 2000", "15 March 1990"])
def test_wealth_ignores_house_system_and_sect(date):
    chart = _by_date(date)
    placidus = _chart(chart, HouseSystem.PLACIDUS)[3]["lot_wealth"]
    whole_sign = _chart(chart, HouseSystem.WHOLE_SIGN)[3]["lot_wealth"]
    assert placidus.longitude == whole_sign.longitude
    assert placidus.formula == whole_sign.formula
    assert not placidus.formula.startswith(("day", "night"))


def test_wealth_ruler_for_every_asc_sign():
    # Over one day in Manila the ASC passes through all 12 signs.
    lat, lon = 14.5833, 121.0
    start = local_to_utc(datetime(2000, 3, 15), lat, lon).julian_day_ut
    seen = {}
    for step in range(96):  # every 15 minutes
        jd = start + step / 96
        points = compute_points(jd).points
        houses = compute_houses(jd, lat, lon, HouseSystem.PLACIDUS)
        sun = next(p for p in points if p.id == "sun")
        sect = compute_sect(jd, lat, lon, sun, houses.angle("asc").longitude)
        wealth = compute_lots(points, houses, sect)[3]
        second = SIGNS[(SIGNS.index(houses.angle("asc").position.sign) + 1) % 12]
        seen[second] = wealth.formula
    assert set(seen) == set(SIGNS)
    for sign, formula in seen.items():
        ruler = TRADITIONAL_RULERS[sign].title()
        assert formula.endswith(f"− {ruler} (ruler of {sign.title()})"), formula
    assert seen["aquarius"].endswith("Saturn (ruler of Aquarius)")
    assert seen["scorpio"].endswith("Mars (ruler of Scorpio)")
    assert seen["pisces"].endswith("Jupiter (ruler of Pisces)")
