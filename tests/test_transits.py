from collections import defaultdict
from datetime import UTC, datetime, timedelta

import pytest
from reference import load_charts, local_datetime

from aster_engine import analysis as A
from aster_engine.ephemeris import calc_body
from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.points import compute_points
from aster_engine.profections import profections
from aster_engine.timeutil import julian_day_ut, local_to_utc
from aster_engine.transits import (
    ASPECT_ANGLES,
    MERGE_GAP_DAYS,
    TRANSITING,
    select,
    targets,
    transit_windows,
)

NOW = datetime(2026, 11, 6, 12, tzinfo=UTC)
CHART = next(c for c in load_charts() if c["birth"]["date"] == "15 March 2000")


def _targets(now=NOW):
    b = CHART["birth"]
    local = local_datetime(CHART)
    jd = local_to_utc(local, b["lat"], b["lon"]).julian_day_ut
    points = compute_points(jd).points
    houses = compute_houses(jd, b["lat"], b["lon"], HouseSystem.PLACIDUS)
    lord = profections(local.date(), now.date(), houses)[0]
    return targets(points, houses, A.chart_ruler(points, houses), lord)


@pytest.fixture(scope="module")
def windows():
    return transit_windows(_targets(), NOW)


def _offset(when, w, natal):
    lon = calc_body(julian_day_ut(when), TRANSITING[w.body])[0]
    return min(abs((lon - natal - a + 180) % 360 - 180) for a in ASPECT_ANGLES[w.aspect])


def test_targets_and_roles():
    ts = {t.id: t.roles for t in _targets()}
    assert list(ts) == ["sun", "moon", "asc", "mc", "mercury", "venus", "mars", "jupiter", "saturn"]
    assert ts["sun"] == ("chart_ruler",)  # ASC Leo
    assert ts["venus"] == ("lord_of_year",)  # age 26, Libra


def test_exact_hits_entries_and_exits(windows):
    natal = {t.id: t.longitude for t in _targets()}
    for w in windows:
        for e in w.exact:
            assert _offset(e, w, natal[w.target]) < 0.01, w
        if not w.starts_before_scan:
            assert _offset(w.start, w, natal[w.target]) == pytest.approx(1, abs=0.01), w
        if not w.ends_after_scan:
            assert _offset(w.end, w, natal[w.target]) == pytest.approx(1, abs=0.01), w


def test_scan_covers_15_years_each_way(windows):
    assert min(w.start for w in windows) >= NOW - timedelta(days=15 * 365.25 + 1)
    assert max(w.end for w in windows) <= NOW + timedelta(days=15 * 365.25 + 1)
    assert {w.body for w in windows} == set(TRANSITING)
    assert {w.aspect for w in windows} == {"conjunction", "opposition", "square", "trine"}


def test_passes_less_than_a_year_apart_are_merged(windows):
    groups = defaultdict(list)
    for w in windows:
        groups[(w.body, w.angle, w.target)].append(w)
    for ws in groups.values():
        ws.sort(key=lambda w: w.start)
        for a, b in zip(ws, ws[1:], strict=False):
            assert (b.start - a.end) >= timedelta(days=MERGE_GAP_DAYS)


def test_saturn_conjunct_sun_2025(windows):
    # Saturn reached 24°58' Pisces in April 2025, went into Aries, and turned
    # back to 25°09' Pisces in November: two passes, one exact hit.
    w = next(
        w
        for w in windows
        if (w.body, w.aspect, w.target) == ("saturn", "conjunction", "sun") and w.start.year == 2025
    )
    assert w.passes == 2
    assert [e.date().isoformat() for e in w.exact] == ["2025-04-05"]
    assert w.status == "past"
    assert w.evidence == ("transit_saturn_conjunction_sun_2025_03",)


def test_pluto_passes_merge_into_one_window(windows):
    w = next(
        w
        for w in windows
        if (w.body, w.aspect, w.target) == ("pluto", "square", "mc") and w.start.year == 2025
    )
    assert w.passes == 4 and len(w.exact) == 3
    assert w.status == "active" and w.in_orb_now


def test_selection(windows):
    result = select(windows, NOW)
    assert set(result.active) == {w for w in windows if w.start <= NOW <= w.end}
    assert len(result.past) == 15 and len(result.upcoming) == 20
    for chosen, status, key in (
        (result.past, "past", lambda w: (w.priority, -w.end.timestamp())),
        (result.upcoming, "upcoming", lambda w: (w.priority, w.start.timestamp())),
    ):
        left_out = [w for w in windows if w.status == status and w not in chosen]
        assert max(map(key, chosen)) <= min(map(key, left_out))
        assert list(chosen) == sorted(chosen, key=lambda w: w.start)


def test_priority():
    ws = {(w.body, w.aspect, w.target): w for w in transit_windows(_targets(), NOW)}
    assert ws[("saturn", "conjunction", "sun")].priority == (0, 0, 0)
    assert ws[("jupiter", "trine", "mars")].priority == (2, 1, 1)
    assert ws[("uranus", "square", "venus")].priority == (1, 1, 0)  # Lord of the Year


def test_user_can_choose_another_date():
    later = datetime(2035, 1, 1, tzinfo=UTC)
    result = select(transit_windows(_targets(later), later), later)
    assert result.now == later
    assert all(w.start <= later <= w.end for w in result.active)
    assert all(w.end < later for w in result.past)
