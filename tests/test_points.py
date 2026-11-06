import shutil

import pytest
import swisseph as swe
from reference import PLANET_TOLERANCE, angle_diff, chart_id, load_charts, local_datetime

from aster_engine.ephemeris import EphemerisFileMissing, ephe_path
from aster_engine.points import POINTS, compute_points
from aster_engine.timeutil import local_to_utc

CHARTS = load_charts()
# Astro.com's id for each point, where it differs.
ASTRO_IDS = {"north_node": "mean_node"}


def _jd(chart):
    b = chart["birth"]
    return local_to_utc(local_datetime(chart), b["lat"], b["lon"]).julian_day_ut


@pytest.fixture(scope="module", params=CHARTS, ids=chart_id)
def chart_points(request):
    chart = request.param
    return chart, {p.id: p for p in compute_points(_jd(chart)).points}


def test_all_points_computed_in_order(chart_points):
    _, points = chart_points
    assert list(points) == [id for id, _ in POINTS]


def test_points_match_astro_com(chart_points):
    chart, points = chart_points
    for id, p in points.items():
        if id == "south_node":
            continue
        ref = chart["bodies"][ASTRO_IDS.get(id, id)]
        assert abs(angle_diff(p.longitude, ref["longitude"])) <= PLANET_TOLERANCE, id
        assert p.position.sign == ref["sign"], id
        assert p.retrograde == (ref["speed"] < 0), id


def test_south_node_opposes_north_node(chart_points):
    _, points = chart_points
    north, south = points["north_node"], points["south_node"]
    assert angle_diff(south.longitude, north.longitude + 180) == pytest.approx(0, abs=1e-9)
    assert south.speed == north.speed


def test_evidence_ids(chart_points):
    _, points = chart_points
    for p in points.values():
        assert p.evidence[0] == f"{p.id}_sign_{p.position.sign}"
        assert (f"{p.id}_retrograde" in p.evidence) == p.retrograde


def test_known_evidence_for_manila_2000():
    chart = next(c for c in CHARTS if c["birth"]["date"] == "15 March 2000")
    points = {p.id: p for p in compute_points(_jd(chart)).points}
    assert points["sun"].evidence == ("sun_sign_pisces",)
    assert points["mars"].evidence == ("mars_sign_aries",)
    assert points["ceres"].evidence == ("ceres_sign_libra", "ceres_retrograde")


def _ephe_without(tmp_path, *missing):
    for f in ephe_path().rglob("*"):
        rel = f.relative_to(ephe_path())
        if f.is_file() and str(rel) not in missing:
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, tmp_path / rel)
    return tmp_path


J2000 = 2451545.0


def test_missing_asteroid_file_skips_only_its_points(tmp_path):
    result = compute_points(J2000, _ephe_without(tmp_path, "seas_18.se1"))
    skipped = {s.id: s.missing_file for s in result.skipped}
    assert skipped == dict.fromkeys(["chiron", "ceres", "pallas", "juno", "vesta"], "seas_18.se1")
    assert "sun" in {p.id for p in result.points}


@pytest.mark.parametrize("file", ["sepl_18.se1", "semo_18.se1"])
def test_missing_required_file_raises(tmp_path, file):
    with pytest.raises(EphemerisFileMissing, match=file):
        compute_points(J2000, _ephe_without(tmp_path, file))


def test_hygiea_skipped_after_its_coverage():
    result = compute_points(swe.julday(2150, 1, 1, 12.0))
    assert [s.id for s in result.skipped] == ["hygiea"]
    assert result.skipped[0].missing_file == "ast0/se00010s.se1"
