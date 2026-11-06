"""Engine output checked against Astro.com reference charts."""

import pytest
from reference import PLANET_TOLERANCE, angle_diff, chart_id, load_charts, local_datetime

from aster_engine.ephemeris import BODIES, calc_body, ephe_path
from aster_engine.timeutil import local_to_utc

CHARTS = load_charts()


def _utc(chart):
    b = chart["birth"]
    return local_to_utc(local_datetime(chart), b["lat"], b["lon"])


@pytest.mark.parametrize("chart", CHARTS, ids=chart_id)
def test_birth_time_to_utc_matches_astro_com(chart):
    # Astro.com shows UT as "H:MM", with "(D Month)" when the UT date differs.
    utc = _utc(chart).utc
    assert chart["ut"].split()[0] == f"{utc.hour}:{utc.minute:02d}"
    if "(" in chart["ut"]:
        assert chart["ut"].split("(")[1].split()[0] == str(utc.day)


CASES = [
    pytest.param(chart, body, id=f"{chart_id(chart)} {body}")
    for chart in CHARTS
    for body in chart["bodies"]
    if body in BODIES
]


@pytest.mark.parametrize("chart,body", CASES)
def test_body_position_matches_astro_com(chart, body):
    file = BODIES[body].file
    if file and not (ephe_path() / file).is_file():
        pytest.skip(f"{file} not bundled")
    ref = chart["bodies"][body]
    lon, _, _, speed, *_ = calc_body(_utc(chart).julian_day_ut, body)
    assert abs(angle_diff(lon, ref["longitude"])) <= PLANET_TOLERANCE
    assert (speed < 0) == (ref["speed"] < 0), "retrograde status differs"
