from datetime import datetime

import pytest
from reference import angle_diff, chart_id, load_charts, local_datetime

from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.points import compute_points
from aster_engine.sect import compute_sect
from aster_engine.timeutil import local_to_utc

CHARTS = load_charts()

# From the Sun's house on Astro.com (7-12 is above the horizon), except
# Tromsø, where the Sun is below the horizon during the polar night.
EXPECTED = {
    "Cebu 1 June 1890": "day",
    "Manila 10 May 1943": "day",
    "Manila 15 June 1978": "day",
    "Manila 15 March 1990": "night",
    "Manila 15 March 2000": "day",
    "Tromsø 1 December 1990": "night",
}


def _sect(jd, lat, lon):
    sun = next(p for p in compute_points(jd).points if p.id == "sun")
    asc = compute_houses(jd, lat, lon, HouseSystem.PLACIDUS).angle("asc").longitude
    return compute_sect(jd, lat, lon, sun, asc), sun, asc


def _chart_sect(chart):
    b = chart["birth"]
    jd = local_to_utc(local_datetime(chart), b["lat"], b["lon"]).julian_day_ut
    return _sect(jd, b["lat"], b["lon"])[0]


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_sect_of_reference_charts(chart):
    sect = _chart_sect(chart)
    assert sect.kind == EXPECTED[chart_id(chart)]
    assert sect.evidence == (f"sect_{sect.kind}",)
    assert (sect.sun_altitude > 0) == (sect.kind == "day")


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_formula_agrees_outside_polar_latitudes(chart):
    sect = _chart_sect(chart)
    polar = chart["birth"]["place"].startswith("Troms")
    assert ("sect_formula_disagrees_high_latitude" in sect.flags) == polar
    assert "sect_unstable_sun_near_horizon" not in sect.flags


def test_tromso_polar_night_is_night_despite_formula():
    tromso = next(c for c in CHARTS if c["birth"]["place"].startswith("Troms"))
    sect = _chart_sect(tromso)
    assert sect.sun_from_asc > 180  # the formula alone would say day
    assert sect.kind == "night"


def test_sun_near_horizon_is_flagged():
    # Scan sunrise in Manila on 15 March 2000 minute by minute.
    lat, lon = 14.5833, 121.0
    start = local_to_utc(datetime(2000, 3, 15, 5, 30), lat, lon).julian_day_ut
    near = []
    for minute in range(90):
        jd = start + minute / 1440
        sect, sun, asc = _sect(jd, lat, lon)
        near.append((abs(angle_diff(sun.longitude, asc)) <= 1, sect))
    flagged = [s for is_near, s in near if is_near]
    assert flagged, "the Sun should cross the ASC within the scan"
    assert all("sect_unstable_sun_near_horizon" in s.flags for s in flagged)
    assert all("sect_unstable_sun_near_horizon" not in s.flags for n, s in near if not n)
    kinds = [s.kind for _, s in near]
    assert kinds[0] == "night" and kinds[-1] == "day"
