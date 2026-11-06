"""Annual profections (spec COMPUTATION step 6g)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .houses import Houses
from .zodiac import SIGNS, TRADITIONAL_RULERS

YEARS_SHOWN = 3  # the current year and the next 2


@dataclass(frozen=True)
class ProfectionYear:
    age: int
    start: date  # birthday that starts the year
    end: date  # next birthday, exclusive
    house: int  # whole sign house from the ASC, 1-12
    sign: str
    lord: str  # Lord of the Year: traditional ruler of the sign
    evidence: tuple[str, ...]


def _birthday(birth: date, year: int) -> date:
    # A 29 February birthday falls on 1 March in common years.
    try:
        return birth.replace(year=year)
    except ValueError:
        return date(year, 3, 1)


def age_on(birth: date, on: date) -> int:
    """Completed years: the age changes on the local birthday."""
    if on < birth:
        raise ValueError(f"{on} is before the birth date {birth}")
    age = on.year - birth.year
    return age if on >= _birthday(birth, on.year) else age - 1


def profection_year(birth: date, asc_sign: str, age: int) -> ProfectionYear:
    house = age % 12 + 1
    sign = SIGNS[(SIGNS.index(asc_sign) + age) % 12]
    lord = TRADITIONAL_RULERS[sign]
    evidence = (
        f"profection_age_{age}_house_{house}",
        f"profection_age_{age}_sign_{sign}",
        f"lord_of_year_age_{age}_{lord}",
    )
    start = _birthday(birth, birth.year + age)
    end = _birthday(birth, birth.year + age + 1)
    return ProfectionYear(age, start, end, house, sign, lord, evidence)


def profections(birth: date, current: date, houses: Houses) -> tuple[ProfectionYear, ...]:
    """Profection years from the one containing `current`, whole sign from the ASC.

    `birth` is the local birth date; age 0 profects the 1st house.
    """
    asc_sign = houses.angle("asc").position.sign
    age = age_on(birth, current)
    return tuple(profection_year(birth, asc_sign, a) for a in range(age, age + YEARS_SHOWN))
