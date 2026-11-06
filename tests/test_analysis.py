"""Expected values worked out by hand from the reference charts' positions."""

import pytest
from reference import load_charts, local_datetime

from aster_engine import analysis as A
from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.points import compute_points
from aster_engine.sect import compute_sect
from aster_engine.timeutil import local_to_utc

CHARTS = {c["birth"]["date"]: c for c in load_charts()}


def _chart(date, system=HouseSystem.PLACIDUS):
    c = CHARTS[date]
    b = c["birth"]
    jd = local_to_utc(local_datetime(c), b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], system)
    sun = next(p for p in points if p.id == "sun")
    sect = compute_sect(jd, b["lat"], b["lon"], sun, houses.angle("asc").longitude)
    return points, houses, sect


# Manila 2000 (day): Sun, Mercury, Venus in Pisces; Moon in Cancer; Mars in
# Aries; Jupiter, Saturn in Taurus; Uranus, Neptune in Aquarius; Pluto in
# Sagittarius; ASC Leo.
M2000 = "15 March 2000"
# Manila 1990 (night): Sun, Mercury in Pisces; Moon, Pluto in Scorpio; Venus,
# Mars in Aquarius; Jupiter in Cancer; Saturn, Uranus, Neptune in Capricorn;
# ASC Sagittarius.
M1990 = "15 March 1990"


def test_sect_roles_day_and_night():
    day = A.sect_roles(_chart(M2000)[2])
    assert (day.sect_light, day.benefic_of_sect, day.malefic_of_sect) == (
        "sun",
        "jupiter",
        "saturn",
    )
    assert (day.benefic_contrary_to_sect, day.malefic_contrary_to_sect) == ("venus", "mars")
    night = A.sect_roles(_chart(M1990)[2])
    assert (night.sect_light, night.benefic_of_sect, night.malefic_of_sect) == (
        "moon",
        "venus",
        "mars",
    )
    assert night.evidence[0] == "sect_light_moon"


@pytest.mark.parametrize(
    "date,expected",
    [
        (
            M2000,
            {
                "sun": (),
                "moon": ("domicile",),
                "mercury": ("detriment", "fall"),
                "venus": ("exaltation",),
                "mars": ("domicile",),
                "jupiter": (),
                "saturn": (),
            },
        ),
        (
            M1990,
            {
                "sun": (),
                "moon": ("fall",),
                "mercury": ("detriment", "fall"),
                "venus": (),
                "mars": (),
                "jupiter": ("exaltation",),
                "saturn": ("domicile",),
            },
        ),
    ],
)
def test_dignities(date, expected):
    result = {d.planet: d.dignities for d in A.dignities(_chart(date)[0])}
    assert result == expected


def test_dignity_tables():
    assert A.DOMICILES["saturn"] == ("capricorn", "aquarius")
    assert A.DOMICILES["sun"] == ("leo",)
    assert A.DETRIMENTS["mars"] == ("libra", "taurus")
    assert A.FALLS["sun"] == "libra" and A.FALLS["saturn"] == "aries"
    assert "uranus" not in A.DOMICILES  # traditional planets only


def test_dispositors_with_loop():
    d = A.dispositors(_chart(M2000)[0])
    assert d.final_dispositors == ("moon", "mars")
    assert d.loops == (("venus", "jupiter"),)
    chains = {x.planet: x.chain for x in d.dispositions}
    assert chains["uranus"] == ("uranus", "saturn", "venus", "jupiter")
    assert chains["sun"] == ("sun", "jupiter", "venus")
    assert "dispositor_loop_venus_jupiter" in d.evidence
    assert "final_dispositor_mars" in d.evidence


def test_single_final_dispositor():
    # Sun -> Jupiter -> Moon -> Mars -> Saturn, in its own Capricorn.
    d = A.dispositors(_chart(M1990)[0])
    assert d.final_dispositors == ("saturn",)
    assert d.loops == ()
    assert all(x.chain[-1] == "saturn" for x in d.dispositions)


def test_mutual_receptions():
    m2000 = {(m.a, m.b): m.kinds for m in A.mutual_receptions(_chart(M2000)[0])}
    # Venus in Pisces (Jupiter's), Jupiter in Taurus (Venus's); Moon in Cancer
    # (Jupiter's exaltation), Jupiter in Taurus (Moon's exaltation).
    assert m2000 == {("venus", "jupiter"): ("domicile",), ("moon", "jupiter"): ("exaltation",)}
    m1990 = {(m.a, m.b): m.kinds for m in A.mutual_receptions(_chart(M1990)[0])}
    # Mars in Aquarius (Saturn's domicile), Saturn in Capricorn (Mars's exaltation).
    assert m1990 == {("mars", "saturn"): ("mixed",)}


def test_house_rulers_and_chart_ruler():
    points, houses, _ = _chart(M2000)
    rulers = {r.house: r for r in A.house_rulers(points, houses)}
    assert (rulers[1].sign, rulers[1].ruler, rulers[1].ruler_house) == ("leo", "sun", 8)
    assert (rulers[2].sign, rulers[2].ruler, rulers[2].ruler_house) == ("virgo", "mercury", 8)
    assert rulers[2].evidence == ("house_2_ruler_mercury", "house_2_ruler_in_house_8")
    cr = A.chart_ruler(points, houses)
    assert (cr.planet, cr.house) == ("sun", 8)
    assert cr.evidence == ("chart_ruler_sun", "chart_ruler_in_house_8")


def test_house_rulers_follow_house_system():
    points, houses, _ = _chart(M2000, HouseSystem.WHOLE_SIGN)
    rulers = A.house_rulers(points, houses)
    assert [r.sign for r in rulers[:3]] == ["leo", "virgo", "libra"]
