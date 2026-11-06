from datetime import date

import pytest
from reference import load_charts, local_datetime

from aster_engine.houses import HouseSystem, compute_houses
from aster_engine.profections import age_on, profection_year, profections
from aster_engine.timeutil import local_to_utc

CHARTS = {c["birth"]["date"]: c for c in load_charts()}


def _houses(date_key, system=HouseSystem.PLACIDUS):
    c = CHARTS[date_key]
    b = c["birth"]
    jd = local_to_utc(local_datetime(c), b["lat"], b["lon"]).julian_day_ut
    return compute_houses(jd, b["lat"], b["lon"], system)


BIRTH_2000 = date(2000, 3, 15)  # Manila, ASC Leo


def test_current_and_next_two_years():
    years = profections(BIRTH_2000, date(2026, 11, 6), _houses("15 March 2000"))
    assert [(y.age, y.house, y.sign, y.lord) for y in years] == [
        (26, 3, "libra", "venus"),
        (27, 4, "scorpio", "mars"),
        (28, 5, "sagittarius", "jupiter"),
    ]
    assert (years[0].start, years[0].end) == (date(2026, 3, 15), date(2027, 3, 15))
    assert years[0].evidence == (
        "profection_age_26_house_3",
        "profection_age_26_sign_libra",
        "lord_of_year_age_26_venus",
    )


def test_year_changes_on_the_birthday():
    houses = _houses("15 March 2000")
    assert profections(BIRTH_2000, date(2026, 3, 14), houses)[0].age == 25
    assert profections(BIRTH_2000, date(2026, 3, 15), houses)[0].age == 26


def test_age_zero_is_the_first_house_and_the_cycle_repeats():
    first = profection_year(BIRTH_2000, "leo", 0)
    assert (first.house, first.sign) == (1, "leo")
    assert profection_year(BIRTH_2000, "leo", 12).sign == "leo"
    assert profection_year(BIRTH_2000, "leo", 1).lord == "mercury"  # Virgo


def test_traditional_rulers():
    # ASC Sagittarius (Manila 1990): age 2 Aquarius -> Saturn, age 3 Pisces -> Jupiter.
    assert profection_year(date(1990, 3, 15), "sagittarius", 2).lord == "saturn"
    assert profection_year(date(1990, 3, 15), "sagittarius", 3).lord == "jupiter"
    assert profection_year(date(1990, 3, 15), "sagittarius", 11).lord == "mars"  # Scorpio


def test_whole_sign_regardless_of_house_system():
    current = date(2026, 11, 6)
    placidus = profections(BIRTH_2000, current, _houses("15 March 2000"))
    whole = profections(BIRTH_2000, current, _houses("15 March 2000", HouseSystem.WHOLE_SIGN))
    assert placidus == whole


def test_leap_day_birthday():
    birth = date(2000, 2, 29)
    assert age_on(birth, date(2001, 2, 28)) == 0
    assert age_on(birth, date(2001, 3, 1)) == 1
    assert age_on(birth, date(2004, 2, 29)) == 4
    assert profection_year(birth, "leo", 1).start == date(2001, 3, 1)


def test_current_date_before_birth_is_an_error():
    with pytest.raises(ValueError):
        age_on(BIRTH_2000, date(1999, 1, 1))
