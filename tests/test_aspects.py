import pytest
from reference import chart_id, load_charts, local_datetime

from aster_engine.aspects import (
    ASPECTS,
    Factor,
    compute_aspects,
    factors,
    find_aspect,
    max_orb,
)
from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.lots import compute_lots
from aster_engine.points import compute_points
from aster_engine.sect import compute_sect
from aster_engine.timeutil import local_to_utc

CHARTS = load_charts()


def _chart(chart):
    b = chart["birth"]
    jd = local_to_utc(local_datetime(chart), b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], HouseSystem.PLACIDUS)
    sun = next(p for p in points if p.id == "sun")
    sect = compute_sect(jd, b["lat"], b["lon"], sun, houses.angle("asc").longitude)
    lots = compute_lots(points, houses, sect)
    return points, houses, lots


@pytest.fixture(scope="module", params=CHARTS, ids=chart_id)
def chart_aspects(request):
    chart = request.param
    points, houses, lots = _chart(chart)
    return chart, factors(points, houses, lots), compute_aspects(points, houses, lots)


def test_astro_com_aspects_within_spec_orbs_are_found(chart_aspects):
    # Astro.com uses wider orbs, so only its aspects within the spec's orbs count.
    chart, fs, aspects = chart_aspects
    by_id = {f.id: f for f in fs}
    ours = {frozenset((x.a, x.b)): x for x in aspects}
    checked = 0
    for ref in chart["aspects"]:
        if ref["aspect"] not in ASPECTS:
            continue
        a, b = by_id[ref["a"]], by_id[ref["b"]]
        found = ours.get(frozenset((a.id, b.id)))
        orb = abs(abs((a.longitude - b.longitude + 180) % 360 - 180) - ASPECTS[ref["aspect"]])
        if orb > max_orb(a, b, ref["aspect"]):
            assert found is None or found.aspect != ref["aspect"]
            continue
        checked += 1
        assert found is not None and found.aspect == ref["aspect"], ref
    assert checked >= 20


def test_applying_matches_astro_com(chart_aspects):
    chart, _, aspects = chart_aspects
    ours = {frozenset((x.a, x.b)): x for x in aspects}
    polar = chart["birth"]["place"].startswith("Troms")
    for ref in chart["aspects"]:
        found = ours.get(frozenset((ref["a"], ref["b"])))
        if found is None or found.aspect != ref["aspect"]:
            continue
        if polar and "asc" in (ref["a"], ref["b"]):
            # The ASC moves backwards at times near the poles; Astro.com assumes
            # it always moves forward. We use its actual motion.
            continue
        assert found.applying == ref["applying"], ref


def test_pairs(chart_aspects):
    _, _, aspects = chart_aspects
    for x in aspects:
        ids = {x.a, x.b}
        assert ids != {"asc", "mc"}
        assert not ids & {"dsc", "ic"}
        assert ids != {"north_node", "south_node"}
        if "south_node" in ids:
            assert x.aspect == "conjunction"
        assert x.orb <= x.max_orb
        assert x.evidence[0] == f"{x.a}_{x.b}_{x.aspect}"


def _f(id, lon, speed=0.0):
    return Factor(id, lon, speed)


@pytest.mark.parametrize(
    "a,b,aspect,orb",
    [
        ("mars", "jupiter", "square", 7),
        ("mars", "jupiter", "quincunx", 3),
        ("sun", "mars", "conjunction", 10),
        ("moon", "venus", "sextile", 6),
        ("sun", "moon", "quincunx", 3),
        ("sun", "asc", "conjunction", 5),  # the angle caps the Sun's orb
        ("mars", "mc", "sextile", 3),
        ("mars", "asc", "quincunx", 1.5),
        ("sun", "chiron", "conjunction", 3),  # the point caps the Sun's orb
        ("asc", "chiron", "trine", 3),
        ("chiron", "lot_fortune", "quincunx", 1.5),
        ("north_node", "vertex", "sextile", 3),
    ],
)
def test_max_orb(a, b, aspect, orb):
    assert max_orb(_f(a, 0), _f(b, 0), aspect) == orb


def test_orb_limit_is_inclusive():
    assert find_aspect(_f("mars", 0), _f("jupiter", 97)).aspect == "square"
    assert find_aspect(_f("mars", 0), _f("jupiter", 97.001)) is None


def test_out_of_sign():
    x = find_aspect(_f("mars", 29.5), _f("jupiter", 31))  # 29°30' Aries, 1° Taurus
    assert x.aspect == "conjunction" and x.out_of_sign
    assert x.evidence == ("mars_jupiter_conjunction", "mars_jupiter_conjunction_out_of_sign")
    y = find_aspect(_f("mars", 10), _f("jupiter", 100))  # Aries, Cancer
    assert y.aspect == "square" and not y.out_of_sign


def test_applying_and_separating():
    # Mars at 0° moving forward, Jupiter fixed at 95°: square tightening, then widening.
    assert find_aspect(_f("mars", 0, 0.5), _f("jupiter", 95)).applying
    assert not find_aspect(_f("mars", 0, 0.5), _f("jupiter", 85)).applying
    # Retrograde motion reverses it.
    assert not find_aspect(_f("mars", 0, -0.5), _f("jupiter", 95)).applying


def test_vertex_and_lots_are_fixed():
    points, houses, lots = _chart(CHARTS[0])
    fs = {f.id: f for f in factors(points, houses, lots)}
    assert fs["vertex"].speed == 0 and fs["lot_fortune"].speed == 0
    assert fs["asc"].speed > 300  # about one degree every four minutes
    assert "dsc" not in fs and "ic" not in fs
