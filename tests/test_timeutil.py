"""Expected offsets come from the IANA tz database (pinned tzdata package)."""

from datetime import datetime, timedelta

import pytest

from aster_engine.timeutil import TimezoneNotFound, local_to_utc, timezone_at

MANILA = (14.5995, 120.9842)


def utc_of(local: str, lat: float, lon: float, **kw):
    return local_to_utc(datetime.fromisoformat(local), lat, lon, **kw)


@pytest.mark.parametrize(
    "local,expected_utc,offset_h,abbr",
    [
        ("2000-06-01T12:00", "2000-06-01T04:00", 8, "PST"),
        ("1943-06-01T12:00", "1943-06-01T03:00", 9, "JST"),  # Japanese occupation
        ("1990-06-01T12:00", "1990-06-01T03:00", 9, "PDT"),  # 1990 daylight saving
        ("1978-06-01T12:00", "1978-06-01T04:00", 8, "PST"),
    ],
)
def test_manila_historical_offsets(local, expected_utc, offset_h, abbr):
    r = utc_of(local, *MANILA)
    assert r.timezone == "Asia/Manila"
    assert r.utc.replace(tzinfo=None) == datetime.fromisoformat(expected_utc)
    assert r.utc_offset == timedelta(hours=offset_h)
    assert r.tz_abbreviation == abbr
    assert r.flags == ()


def test_manila_before_1899_is_local_mean_time():
    r = utc_of("1890-06-01T12:00", *MANILA)
    assert r.utc_offset == timedelta(hours=8, minutes=3, seconds=52)
    assert "local_mean_time" in r.flags


def test_manila_before_1845_was_on_the_american_side_of_the_date_line():
    r = utc_of("1840-06-01T12:00", *MANILA)
    assert r.utc_offset == -timedelta(hours=15, minutes=56, seconds=8)
    assert r.utc.date().isoformat() == "1840-06-02"


def test_julian_day_j2000():
    # UT1 differs from UTC by under a second.
    assert utc_of("2000-01-01T12:00", 51.4779, 0.0).julian_day_ut == pytest.approx(
        2451545.0, abs=1e-5
    )


def test_ambiguous_time_is_flagged_and_fold_selects_occurrence():
    first = utc_of("2021-11-07T01:30", 40.7128, -74.006)
    second = utc_of("2021-11-07T01:30", 40.7128, -74.006, fold=1)
    assert first.flags == ("ambiguous_local_time",)
    assert second.utc - first.utc == timedelta(hours=1)


def test_nonexistent_time_is_flagged():
    assert utc_of("2021-03-14T02:30", 40.7128, -74.006).flags == ("nonexistent_local_time",)


def test_aware_datetime_rejected():
    with pytest.raises(ValueError):
        local_to_utc(datetime.fromisoformat("2000-01-01T12:00+08:00"), *MANILA)


@pytest.mark.parametrize("lat,lon", [(91, 0), (0, 181)])
def test_invalid_coordinates(lat, lon):
    with pytest.raises(ValueError):
        timezone_at(lat, lon)


def test_timezone_not_found_is_a_value_error():
    assert issubclass(TimezoneNotFound, ValueError)
