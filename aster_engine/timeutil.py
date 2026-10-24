"""Birth time to UTC, using the historical offset of the place on that date."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from importlib import resources
from zoneinfo import ZoneInfo

import swisseph as swe
import tzdata
from timezonefinder import TimezoneFinder

TZDATA_VERSION = tzdata.IANA_VERSION


class TimezoneNotFound(ValueError):
    pass


@dataclass(frozen=True)
class UtcConversion:
    local: datetime  # naive local birth time, as given
    utc: datetime
    timezone: str  # IANA name
    utc_offset: timedelta
    tz_abbreviation: str  # e.g. "PST", "JST", "LMT"
    julian_day_ut: float
    flags: tuple[str, ...]  # "ambiguous_local_time", "nonexistent_local_time", "local_mean_time"


@cache
def _finder() -> TimezoneFinder:
    return TimezoneFinder()


@cache
def _zone(name: str) -> ZoneInfo:
    # Always read from the pinned tzdata package, never the OS copy, so results
    # are reproducible across machines.
    with resources.files("tzdata.zoneinfo").joinpath(*name.split("/")).open("rb") as f:
        return ZoneInfo.from_file(f, key=name)


def timezone_at(lat: float, lon: float) -> str:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")
    name = _finder().timezone_at(lat=lat, lng=lon)
    if name is None:
        raise TimezoneNotFound(f"No timezone found for lat={lat}, lon={lon}")
    return name


def julian_day_ut(utc: datetime) -> float:
    """Julian day (UT1) for a UTC datetime, Gregorian calendar."""
    sec = utc.second + utc.microsecond / 1e6
    _, jd_ut = swe.utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, sec, swe.GREG_CAL)
    return jd_ut


def local_to_utc(local: datetime, lat: float, lon: float, fold: int = 0) -> UtcConversion:
    """Convert a naive local birth time at (lat, lon) to UTC.

    `fold` picks the occurrence of an ambiguous local time (0 = first, 1 = second),
    following PEP 495. Ambiguous and nonexistent local times are flagged, never
    silently resolved.
    """
    if local.tzinfo is not None:
        raise ValueError("local must be a naive datetime (local clock time of the birth place)")
    name = timezone_at(lat, lon)
    zone = _zone(name)
    aware = local.replace(tzinfo=zone, fold=fold)

    flags = []
    other = local.replace(tzinfo=zone, fold=1 - fold)
    if aware.utcoffset() != other.utcoffset():
        roundtrip = aware.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        flags.append("nonexistent_local_time" if roundtrip != local else "ambiguous_local_time")
    abbr = aware.tzname() or ""
    if abbr == "LMT":
        flags.append("local_mean_time")

    utc = aware.astimezone(UTC)
    return UtcConversion(
        local=local,
        utc=utc,
        timezone=name,
        utc_offset=aware.utcoffset(),
        tz_abbreviation=abbr,
        julian_day_ut=julian_day_ut(utc),
        flags=tuple(flags),
    )
