import pytest
from reference import ANGLE_TOLERANCE, angle_diff, chart_id, load_charts, local_datetime

from aster_engine.houses import (
    HouseSystem,
    compute_houses,
    house_of,
    place_points,
    whole_sign_cusps,
)
from aster_engine.points import compute_points
from aster_engine.timeutil import local_to_utc

CHARTS = load_charts()
PLACIDUS_CHARTS = [c for c in CHARTS if c["house_system"] == "Plac"]
TROMSO = next(c for c in CHARTS if c["birth"]["place"].startswith("Troms"))
ASTRO_IDS = {"north_node": "mean_node"}


def _args(chart):
    b = chart["birth"]
    return local_to_utc(local_datetime(chart), b["lat"], b["lon"]).julian_day_ut, b["lat"], b["lon"]


def _near(a, b):
    return abs(angle_diff(a, b)) <= ANGLE_TOLERANCE


@pytest.mark.parametrize("chart", PLACIDUS_CHARTS, ids=chart_id)
def test_placidus_matches_astro_com(chart):
    jd, lat, lon = _args(chart)
    h = compute_houses(jd, lat, lon, HouseSystem.PLACIDUS)
    assert h.system is HouseSystem.PLACIDUS and h.flags == ()
    for i, cusp in enumerate(h.cusps):
        assert _near(cusp, chart["cusps"][str(i + 1)]["longitude"]), f"cusp {i + 1}"
    vertex = chart["bodies"]["vertex"]
    assert _near(h.angle("vertex").longitude, vertex["longitude"])
    assert h.angle("vertex").house == vertex["house"]

    points = compute_points(jd).points
    for ph in place_points(points, h):
        if ph.id != "south_node":
            assert ph.house == chart["bodies"][ASTRO_IDS.get(ph.id, ph.id)]["house"], ph.id


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_angles_match_astro_com_in_any_system(chart):
    jd, lat, lon = _args(chart)
    for system in HouseSystem:
        h = compute_houses(jd, lat, lon, system)
        assert _near(h.angle("asc").longitude, chart["cusps"]["1"]["longitude"])
        assert _near(h.angle("mc").longitude, chart["cusps"]["10"]["longitude"])
        assert _near(h.angle("dsc").longitude, chart["cusps"]["7"]["longitude"])
        assert _near(h.angle("ic").longitude, chart["cusps"]["4"]["longitude"])


def test_tromso_placidus_falls_back_to_whole_sign():
    jd, lat, lon = _args(TROMSO)
    h = compute_houses(jd, lat, lon, HouseSystem.PLACIDUS)
    assert h.requested is HouseSystem.PLACIDUS
    assert h.system is HouseSystem.WHOLE_SIGN
    assert h.flags == ("placidus_unavailable_high_latitude",)
    assert h.cusps == whole_sign_cusps(h.angle("asc").longitude)


def test_whole_sign_houses_count_signs_from_asc():
    chart = next(c for c in CHARTS if c["birth"]["date"] == "15 March 2000")
    jd, lat, lon = _args(chart)
    h = compute_houses(jd, lat, lon, HouseSystem.WHOLE_SIGN)
    assert h.flags == ()
    assert h.cusps[0] == 120.0  # ASC 4° Leo
    assert h.evidence[0] == "house_1_sign_leo" and h.evidence[1] == "house_2_sign_virgo"
    houses = {ph.id: ph.house for ph in place_points(compute_points(jd).points, h)}
    assert houses["sun"] == 8  # Pisces
    assert houses["moon"] == 12  # Cancer
    assert houses["mars"] == 9  # Aries


def test_evidence_ids():
    chart = next(c for c in CHARTS if c["birth"]["date"] == "15 March 2000")
    jd, lat, lon = _args(chart)
    h = compute_houses(jd, lat, lon, HouseSystem.PLACIDUS)
    assert h.angle("asc").evidence == ("asc_sign_leo",)
    assert h.angle("mc").evidence == ("mc_sign_taurus",)
    assert h.angle("vertex").evidence == ("vertex_sign_scorpio", "vertex_house_4")
    sun = next(ph for ph in place_points(compute_points(jd).points, h) if ph.id == "sun")
    assert sun.evidence == "sun_house_8"


@pytest.mark.parametrize(
    "lon,house",
    [(10, 1), (29.999, 1), (30, 2), (355, 12), (0, 1), (-5, 12)],
)
def test_house_of_whole_sign(lon, house):
    assert house_of(lon, whole_sign_cusps(15)) == house


def test_house_of_handles_cusp_crossing_aries():
    cusps = (350.0, 20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 320.0)
    assert house_of(355, cusps) == 1
    assert house_of(5, cusps) == 1
    assert house_of(20, cusps) == 2
    assert house_of(345, cusps) == 12
